# -*- coding: utf-8 -*-
"""Veritabanı başlatma scripti"""

import os
import sys

# Script olarak çalıştırılıyorsa Backend'i path'e ekle
if __name__ == "__main__":
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)

from database.connection import engine, DATABASE_PATH
from database.models import Base


def init_database():
    """Tüm tabloları oluştur"""
    print(f"Initializing database at: {DATABASE_PATH}")

    # Tüm tabloları oluştur
    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully!")
    print("\nTables created:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")


def drop_all_tables():
    """Tüm tabloları sil (dikkatli kullanın!)"""
    print("WARNING: This will delete all data!")
    confirm = input("Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped.")
    else:
        print("Cancelled.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database management")
    parser.add_argument('--drop', action='store_true', help='Drop all tables')
    args = parser.parse_args()

    if args.drop:
        drop_all_tables()
    else:
        init_database()
