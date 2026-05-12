"""
db_explorer.py — Interactive Database Explorer for Skintify
"""

import os
import sys
import questionary
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Fix Pathing
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.engine import engine, SessionLocal

def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

def show_table_content(table_name, limit=20):
    print(f"\n--- [ TABLE: {table_name} ] (First {limit} rows) ---")
    
    with SessionLocal() as session:
        # Use textual SQL for dynamic table exploration
        result = session.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
        columns = result.keys()
        rows = result.fetchall()
        
        if not rows:
            print("  (Table is empty)")
            return

        # Simple manual formatting
        # Header
        header = " | ".join([str(c).upper() for c in columns])
        print("  " + header)
        print("  " + "-" * len(header))
        
        # Rows
        for row in rows:
            formatted_row = []
            for val in row:
                s_val = str(val)
                if len(s_val) > 30:
                    s_val = s_val[:27] + "..."
                formatted_row.append(s_val)
            print("  " + " | ".join(formatted_row))
    print("-" * 60)

def main():
    while True:
        tables = get_table_names()
        if not tables:
            print("❌ No tables found in database. Please run 'Setup Database' first.")
            break
            
        # Fetch row counts for each table
        table_choices = []
        with SessionLocal() as session:
            for t in tables:
                try:
                    count = session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                    table_choices.append(f"{t:<20} ({count} records)")
                except:
                    table_choices.append(f"{t:<20} (Error counting)")

        print("\n--- DATABASE EXPLORER ---")
        choice_raw = questionary.select(
            "Pilih Tabel untuk Dilihat:",
            choices=table_choices + ["Kembali"]
        ).ask()
        
        if choice_raw == "Kembali" or choice_raw is None:
            break
            
        # Extract table name from choice string
        choice = choice_raw.split()[0]
        show_table_content(choice)
        input("\nTekan Enter untuk kembali ke daftar tabel...")

if __name__ == "__main__":
    main()
