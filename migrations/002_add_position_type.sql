-- Add Position Type to Watchlist
-- Created: 2026-01-06
-- Purpose: Allow users to mark stocks as Long/Short/Watch/Wishlist

-- ============================================================================
-- FORWARD MIGRATION
-- ============================================================================

-- Step 1: Add position_type column with default 'watch'
ALTER TABLE user_watchlist
ADD COLUMN IF NOT EXISTS position_type VARCHAR(20) DEFAULT 'watch';

-- Step 2: Add check constraint for valid position types
ALTER TABLE user_watchlist
ADD CONSTRAINT check_position_type
CHECK (position_type IN ('long', 'short', 'watch', 'wishlist'));

-- Step 3: Update existing records to 'watch' (if NULL)
UPDATE user_watchlist
SET position_type = 'watch'
WHERE position_type IS NULL;

-- Step 4: Make position_type NOT NULL
ALTER TABLE user_watchlist
ALTER COLUMN position_type SET NOT NULL;

-- Step 5: Create index for filtering by position type
CREATE INDEX IF NOT EXISTS idx_user_watchlist_position
ON user_watchlist(user_id, position_type, is_active);

-- Step 6: Verify migration
SELECT
    position_type,
    COUNT(*) as count,
    COUNT(DISTINCT user_id) as users
FROM user_watchlist
WHERE is_active = true
GROUP BY position_type;

-- ============================================================================
-- ROLLBACK SCRIPT (commented out - uncomment if you need to rollback)
-- ============================================================================

/*
-- WARNING: This will lose position type data

-- Step 1: Drop index
DROP INDEX IF EXISTS idx_user_watchlist_position;

-- Step 2: Drop constraint
ALTER TABLE user_watchlist DROP CONSTRAINT IF EXISTS check_position_type;

-- Step 3: Remove position_type column
ALTER TABLE user_watchlist DROP COLUMN IF EXISTS position_type;

-- Step 4: Verify rollback
SELECT COUNT(*) as watchlist_entries FROM user_watchlist WHERE is_active = true;
*/
