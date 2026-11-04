const enc = new TextEncoder();

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Authorization, Content-Type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Content-Type": "application/json; charset=utf-8"
};

const out = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: cors
  });

const b64u = b =>
  btoa(String.fromCharCode(...new Uint8Array(b)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");

const unb64u = s =>
  Uint8Array.from(
    atob(s.replace(/-/g, "+").replace(/_/g, "/") +
    "=".repeat((4 - s.length % 4) % 4)),
    c => c.charCodeAt(0)
  );

function requireDB(env) {
  if (!env.DB) throw new Error("D1_BINDING_MISSING");
  return env.DB;
}

async function pwHash(password, salt) {
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"]
  );

  const bits = await crypto.subtle.deriveBits({
    name: "PBKDF2",
    salt: enc.encode(salt),
    iterations: 100000,
    hash: "SHA-256"
  }, key, 256);

  return b64u(bits);
}

async function tokenFor(username, env) {
  if (!env.TOKEN_SECRET) throw new Error("TOKEN_SECRET_MISSING");

  const payload = b64u(enc.encode(JSON.stringify({
    u: username,
    e: Math.floor(Date.now() / 1000) + 86400 * 7
  })));

  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(env.TOKEN_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const sig = b64u(await crypto.subtle.sign(
    "HMAC", key, enc.encode(payload)
  ));

  return payload + "." + sig;
}

async function auth(req, env) {
  try {
    if (!env.TOKEN_SECRET) return null;

    const token = (req.headers.get("Authorization") || "")
      .replace(/^Bearer\s+/i, "");

    const parts = token.split(".");
    if (parts.length !== 2) return null;

    const [p, s] = parts;

    const key = await crypto.subtle.importKey(
      "raw",
      enc.encode(env.TOKEN_SECRET),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["verify"]
    );

    const valid = await crypto.subtle.verify(
      "HMAC", key, unb64u(s), enc.encode(p)
    );

    if (!valid) return null;

    const payload = JSON.parse(
      new TextDecoder().decode(unb64u(p))
    );

    if (!payload.u || payload.e < Date.now() / 1000) return null;

    return payload.u;
  } catch {
    return null;
  }
}

async function body(req) {
  try {
    return await req.json();
  } catch {
    return {};
  }
}

async function publicRoom(DB) {
  return DB.prepare(
    "SELECT id, name, type, owner FROM rooms WHERE type='public' ORDER BY id LIMIT 1"
  ).first();
}

async function fetchHandler(req, env) {
  const url = new URL(req.url);
  const path = url.pathname;

  if (req.method === "OPTIONS") {
    return new Response(null, { headers: cors });
  }

  if (path === "/") {
    return out({
      ok: true,
      name: "MSGN Messenger",
      version: "1.1",
      signature: "m_sgn"
    });
  }

  if (path === "/favicon.ico") {
    return new Response(null, { status: 204 });
  }

  if (path === "/health") {
    return out({
      ok: true,
      service: "MSGN Messenger API",
      version: "1.1"
    });
  }

  // REGISTER
  if (path === "/register" && req.method === "POST") {
    try {
      const b = await body(req);

      const name = String(b.username || "").trim();
      const pass = String(b.password || "");

      if (!/^[a-z]{5,20}$/.test(name)) {
        return out({
          error: "Username must contain 5-20 lowercase English letters."
        }, 400);
      }

      if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])[A-Za-z0-9]{8}$/.test(pass)) {
        return out({
          error: "Password must be exactly 8 characters with uppercase, lowercase and number."
        }, 400);
      }

      const DB = requireDB(env);
      const salt = crypto.randomUUID();
      const hash = await pwHash(pass, salt);

      await DB.prepare(
        `INSERT INTO users
         (username, password_hash, salt, created_at)
         VALUES (?, ?, ?, ?)`
      ).bind(
        name,
        hash,
        salt,
        new Date().toISOString()
      ).run();

      return out({
        ok: true,
        username: name
      }, 201);

    } catch (err) {
      const message = String(err?.message || err);

      if (message.includes("UNIQUE constraint failed")) {
        return out({ error: "Username already exists." }, 409);
      }

      console.error("REGISTER_ERROR:", err?.stack || message);
      return out({ error: "Registration failed." }, 500);
    }
  }

  // LOGIN
  if (path === "/login" && req.method === "POST") {
    try {
      const b = await body(req);
      const name = String(b.username || "").trim();
      const pass = String(b.password || "");

      if (!name || !pass) {
        return out({ error: "Username and password required." }, 400);
      }

      const DB = requireDB(env);

      const user = await DB.prepare(
        `SELECT username, password_hash, salt
         FROM users WHERE username = ?`
      ).bind(name).first();

      if (!user) {
        return out({ error: "Invalid username or password." }, 401);
      }

      const hash = await pwHash(pass, user.salt);

      if (hash !== user.password_hash) {
        return out({ error: "Invalid username or password." }, 401);
      }

      return out({
        ok: true,
        token: await tokenFor(name, env),
        username: name
      });

    } catch (err) {
      console.error("LOGIN_ERROR:", err?.stack || String(err));
      return out({ error: "Login failed." }, 500);
    }
  }

  // AUTHENTICATION
  const user = await auth(req, env);

  if (!user) {
    return out({ error: "Authentication required." }, 401);
  }

  try {
    const DB = requireDB(env);

    // PROFILE
    if (path === "/me" && req.method === "GET") {
      return out({ username: user });
    }

    // PUBLIC ROOM
    if (path === "/rooms" && req.method === "GET") {
      const room = await publicRoom(DB);

      if (!room) {
        return out({ error: "Public room not found." }, 404);
      }

      return out({ rooms: [room] });
    }

    // DISABLE OLD ROOM FEATURES
    if (
      path === "/join" ||
      path === "/dm" ||
      path === "/members" ||
      (path === "/rooms" && req.method === "POST")
    ) {
      return out({
        error: "This feature is disabled in MSGN 1.1."
      }, 410);
    }

    // GET MESSAGES
    if (path === "/messages" && req.method === "GET") {
      const room = await publicRoom(DB);

      if (!room) {
        return out({ error: "Public room not found." }, 404);
      }

      const requestedRoom = Number(
        url.searchParams.get("room_id") || room.id
      );

      if (requestedRoom !== room.id) {
        return out({ error: "Only Public Chat is available." }, 403);
      }

      const afterRaw = url.searchParams.get("after");
      const beforeRaw = url.searchParams.get("before");

      const after = afterRaw === null ? 0 : Number(afterRaw);
      const before = beforeRaw === null ? 0 : Number(beforeRaw);

      if (
        !Number.isSafeInteger(after) ||
        !Number.isSafeInteger(before) ||
        after < 0 ||
        before < 0 ||
        (after > 0 && before > 0)
      ) {
        return out({ error: "Invalid pagination parameters." }, 400);
      }

      const limit = Math.min(
        100,
        Math.max(1, Number(url.searchParams.get("limit") || 50))
      );

      let result;
      let hasMore = false;

      if (after > 0) {
        result = await DB.prepare(
          `SELECT id, room_id, username, message, created_at
           FROM messages
           WHERE room_id = ? AND id > ?
           ORDER BY id ASC
           LIMIT ?`
        ).bind(room.id, after, limit).all();

      } else if (before > 0) {
        const rows = await DB.prepare(
          `SELECT id, room_id, username, message, created_at
           FROM messages
           WHERE room_id = ? AND id < ?
           ORDER BY id DESC
           LIMIT ?`
        ).bind(room.id, before, limit + 1).all();

        hasMore = rows.results.length > limit;
        result = { results: rows.results.slice(0, limit).reverse() };

      } else {
        const rows = await DB.prepare(
          `SELECT id, room_id, username, message, created_at
           FROM messages
           WHERE room_id = ?
           ORDER BY id DESC
           LIMIT ?`
        ).bind(room.id, limit + 1).all();

        hasMore = rows.results.length > limit;
        result = { results: rows.results.slice(0, limit).reverse() };
      }

      return out({
        room,
        messages: result.results,
        has_more: hasMore
      });
    }

    // SEND MESSAGE
    if (path === "/messages" && req.method === "POST") {
      const b = await body(req);
      const room = await publicRoom(DB);

      if (!room) {
        return out({ error: "Public room not found." }, 404);
      }

      const id = b.room_id === undefined
        ? room.id
        : Number(b.room_id);

      const msg = String(b.message || "").trim();

      if (id !== room.id) {
        return out({ error: "Only Public Chat is available." }, 403);
      }

      if (!msg || msg.length > 2000) {
        return out({
          error: "Message must contain 1-2000 characters."
        }, 400);
      }

      const result = await DB.prepare(
        `INSERT INTO messages
         (room_id, username, message, created_at)
         VALUES (?, ?, ?, ?)`
      ).bind(
        room.id,
        user,
        msg,
        new Date().toISOString()
      ).run();

      return out({
        ok: true,
        id: result.meta.last_row_id
      }, 201);
    }

    return out({ error: "Not found." }, 404);

  } catch (err) {
    console.error("API_ERROR:", err?.stack || String(err));
    return out({ error: "Internal server error." }, 500);
  }
}

export default {
  async fetch(req, env) {
    try {
      return await fetchHandler(req, env);
    } catch (err) {
      console.error("WORKER_FATAL:", err?.stack || String(err));
      return out({ error: "Worker internal error." }, 500);
    }
  }
};
