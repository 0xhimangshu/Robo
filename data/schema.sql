-- ticket table
CREATE TABLE IF NOT EXISTS tickkets (
    ticket_guild_id INTEGER PRIMARY KEY,
    ticket_category_id INTEGER,
    ticket_channel_id INTEGER,
    ticket_logs_channel_id INTEGER,
    ticket_ping_role_id INTEGER
)

-- afk table 

CREATE TABLE IF NOT EXISTS afk (
    afk_user_id INTEGER PRIMARY KEY,
    afk_reason TEXT,
    afk_global BOOLEAN,
    afk_mentions INTEGER,
    afk_guild INTEGER
)

-- tag table 
CREATE TABLE IF NOT EXISTS tags (
    tag_id TEXT PRIMARY KEY,
    tag_name TEXT,
    tag_content TEXT,
    tag_owner_id INTEGER,
    tag_guild_id INTEGER,
    tag_uses INTEGER,
    tag_created_at TEXT
)

-- no_prefix table
CREATE TABLE IF NOT EXISTS no_prefix (
    user_id INTEGER PRIMARY KEY
)

-- sticky message table
-- CREATE TABLE IF NOT EXISTS sticky (
--     sticky_guild_id INTEGER PRIMARY KEY,
--     sticky_channel_id INTEGER,
--     sticky_message TEXT
-- )

-- guild table
CREATE TABLE IF NOT EXISTS guilds (
    guild_id INTEGER PRIMARY KEY,
    -- prefix TEXT
)

-- welcome table
CREATE TABLE IF NOT EXISTS welcome (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    msg TEXT,
    img TEXT
)