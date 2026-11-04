CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL,
 salt TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rooms (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 type TEXT NOT NULL CHECK(type IN ('public','group','direct')),
 owner TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS room_members (
 room_id INTEGER NOT NULL,
 username TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'member',
 PRIMARY KEY(room_id,username),
 FOREIGN KEY(room_id) REFERENCES rooms(id)
);
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 room_id INTEGER NOT NULL,
 username TEXT NOT NULL,
 message TEXT NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY(room_id) REFERENCES rooms(id)
);
CREATE INDEX IF NOT EXISTS idx_messages_room_id ON messages(room_id,id);
CREATE INDEX IF NOT EXISTS idx_members_username ON room_members(username);

INSERT OR IGNORE INTO rooms(id,name,type,owner,created_at) VALUES(1,'عمومی','public','system','2026-01-01T00:00:00Z');
