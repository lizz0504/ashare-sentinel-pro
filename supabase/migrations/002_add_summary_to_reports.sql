-- Add summary column to reports table
ALTER TABLE reports ADD COLUMN IF NOT EXISTS summary TEXT;
