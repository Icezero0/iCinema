SELECT name FROM sqlite_master WHERE type='table';
-- PRAGMA table_info(rooms);
-- PRAGMA table_info(room_members);
-- PRAGMA table_info(messages);
-- PRAGMA table_info(notifications);
-- PRAGMA table_info(users);
-- PRAGMA table_info(room_join_requests);
-- PRAGMA table_info(user_sticker_library_items);
-- PRAGMA table_info(emojis);
-- PRAGMA table_info(user_emoji_usages);

-- DROP TABLE IF EXISTS emojis;
-- DROP TABLE IF EXISTS user_emoji_usages;

-- DELETE FROM messages;


-- SELECT * FROM messages;
-- SELECT * FROM room_members;
-- SELECT * FROM users;
-- SELECT * FROM media_assets;
-- SELECT * FROM user_avatar_assets;
-- SELECT * FROM media_assets WHERE asset_type = 'avatar';
-- SELECT * FROM user_avatar_assets WHERE is_deleted = 0;
-- DROP TABLE IF EXISTS messages;


SELECT * FROM rooms;
SELECT * FROM room_settings;

DROP TABLE IF EXISTS room_settings;