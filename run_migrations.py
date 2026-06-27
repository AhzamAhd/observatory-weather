#!/usr/bin/env python3
"""
Run database migrations to set up auth tables.
Run this once before deploying the app.
"""
import db
import sys

def run_migrations():
    """Execute all migration SQL files."""
    try:
        # Read and execute the migration SQL
        with open("migrations/001_add_auth_tables.sql", "r") as f:
            sql = f.read()

        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql.split(';') if s.strip()]

        for stmt in statements:
            print(f"Executing: {stmt[:60]}...")
            db.execute(stmt)

        print("\nMigrations completed successfully!")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
