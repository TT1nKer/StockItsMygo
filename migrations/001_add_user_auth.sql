-- Multi-User Authentication Migration
-- Created: 2026-01-05
-- Purpose: Add user authentication system with user-specific watchlists

-- ============================================================================
-- FORWARD MIGRATION
-- ============================================================================

-- Step 1: Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Step 2: Create default admin user
-- Password: admin123 (CHANGE THIS IMMEDIATELY AFTER SETUP!)
INSERT INTO users (id, username, password_hash, is_active)
VALUES (
    1,
    'admin',
    'pbkdf2:sha256:1000000$uMOZ8onbVuFAXc1o$a939111536d66f12773b530fa038eb193f785261dcf52148aeed38607eae0232',
    true
)
ON CONFLICT (id) DO NOTHING;

-- Step 2a: Fix sequence (since we explicitly set id=1)
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users));

-- Step 3: Add user_id column to user_watchlist (nullable for now)
ALTER TABLE user_watchlist ADD COLUMN IF NOT EXISTS user_id INTEGER;

-- Step 4: Migrate existing watchlist entries to admin user
UPDATE user_watchlist SET user_id = 1 WHERE user_id IS NULL;

-- Step 5: Make user_id NOT NULL
ALTER TABLE user_watchlist ALTER COLUMN user_id SET NOT NULL;

-- Step 6: Add foreign key constraint
ALTER TABLE user_watchlist
  ADD CONSTRAINT fk_user_watchlist_user
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Step 7: Drop old UNIQUE constraint on symbol only
ALTER TABLE user_watchlist DROP CONSTRAINT IF EXISTS user_watchlist_symbol_key;

-- Step 8: Add new composite UNIQUE constraint (user_id + symbol)
ALTER TABLE user_watchlist
  ADD CONSTRAINT unique_user_symbol
  UNIQUE (user_id, symbol);

-- Step 9: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_watchlist_user ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_user_watchlist_active ON user_watchlist(user_id, is_active);

-- Step 10: Verify migration
SELECT
    COUNT(*) as total_watchlist_entries,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT symbol) as unique_symbols
FROM user_watchlist;

SELECT
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE is_active = true) as active_users
FROM users;

-- ============================================================================
-- ROLLBACK SCRIPT (commented out - uncomment if you need to rollback)
-- ============================================================================

/*
-- WARNING: This will lose multi-user data and revert to single-user mode

-- Step 1: Remove indexes
DROP INDEX IF EXISTS idx_user_watchlist_active;
DROP INDEX IF EXISTS idx_user_watchlist_user;

-- Step 2: Drop composite unique constraint
ALTER TABLE user_watchlist DROP CONSTRAINT IF EXISTS unique_user_symbol;

-- Step 3: Drop foreign key
ALTER TABLE user_watchlist DROP CONSTRAINT IF EXISTS fk_user_watchlist_user;

-- Step 4: Remove user_id column
ALTER TABLE user_watchlist DROP COLUMN IF EXISTS user_id;

-- Step 5: Re-add old UNIQUE constraint
ALTER TABLE user_watchlist ADD CONSTRAINT user_watchlist_symbol_key UNIQUE (symbol);

-- Step 6: Drop users table
DROP TABLE IF EXISTS users;

-- Step 7: Verify rollback
SELECT COUNT(*) as watchlist_entries FROM user_watchlist;
*/
