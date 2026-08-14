#!/usr/bin/env python3
"""
Run database migrations to set up auth/saves tables.
Runs every migrations/*.sql file in filename order. Each file uses
CREATE TABLE IF NOT EXISTS, so re-running is safe.
"""
import db
import sys
import glob
import os

def run_migrations():
    """Execute all migration SQL files in order."""
    try:
        files = sorted(glob.glob("migrations/*.sql"))
        if not files:
            print("No migration files found in migrations/")
            return False

        for path in files:
            print(f"\n--- {os.path.basename(path)} ---")
            with open(path, "r") as f:
                sql = f.read()

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
