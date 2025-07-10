#!/usr/bin/env python3
"""
Migration script to add chat_type column to existing chats table.
This script should be run once to update existing databases.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_chat_type():
    """Add chat_type column to chats table if it doesn't exist."""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Create database engine
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if chat_type column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'chats' AND column_name = 'chat_type'
            """))
            
            if result.fetchone():
                print("chat_type column already exists. Migration not needed.")
                return
            
            # Add chat_type column with default value
            print("Adding chat_type column to chats table...")
            conn.execute(text("""
                ALTER TABLE chats 
                ADD COLUMN chat_type VARCHAR DEFAULT 'genetic'
            """))
            
            # Update existing records to have 'genetic' as chat_type
            print("Updating existing chat records...")
            conn.execute(text("""
                UPDATE chats 
                SET chat_type = 'genetic' 
                WHERE chat_type IS NULL
            """))
            
            conn.commit()
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_chat_type() 