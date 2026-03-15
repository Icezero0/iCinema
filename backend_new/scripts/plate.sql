SELECT name FROM sqlite_master WHERE type='table';
PRAGMA table_info(rooms);
PRAGMA table_info(room_members);
PRAGMA table_info(messages);
PRAGMA table_info(notifications);
PRAGMA table_info(users);
PRAGMA index_list(users);