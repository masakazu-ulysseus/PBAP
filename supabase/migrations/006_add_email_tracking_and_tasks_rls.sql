-- Migration: 006_add_email_tracking_and_tasks_rls
-- Description: Add email tracking columns to tasks table and RLS policies for tasks/task_details
-- Date: 2024-12-18

-- Add email tracking columns to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS email_error TEXT;

-- Add RLS policies for tasks table
CREATE POLICY "Public read access for tasks" ON tasks FOR SELECT USING (true);
CREATE POLICY "Enable insert for anon" ON tasks FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON tasks FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON tasks FOR DELETE USING (true);

-- Add RLS policies for task_details table
CREATE POLICY "Public read access for task_details" ON task_details FOR SELECT USING (true);
CREATE POLICY "Enable insert for anon" ON task_details FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON task_details FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON task_details FOR DELETE USING (true);
