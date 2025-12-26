-- Migration: 009_add_user_memo
-- Description: Add user_memo field to tasks table for user's note to company
-- Date: 2025-12-25

-- Add user_memo column after warranty_code
ALTER TABLE tasks
ADD COLUMN user_memo TEXT;

-- Add comment for documentation
COMMENT ON COLUMN tasks.user_memo IS 'ユーザーから弊社への連絡事項';
