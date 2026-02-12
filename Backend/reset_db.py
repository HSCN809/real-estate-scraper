# -*- coding: utf-8 -*-
"""
Veritabanini tamamen temizler.
Tablolari silip yeniden olusturur. Kullanici verileri dahil her sey sifirlanir.

Kullanim:
  docker exec real-estate-api python reset_db.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import engine
from database.models import Base

def reset_database():
    print("Tum tablolar siliniyor...")
    Base.metadata.drop_all(bind=engine)
    print("Tablolar yeniden olusturuluyor...")
    Base.metadata.create_all(bind=engine)
    print("Veritabani sifirlandi.")

if __name__ == "__main__":
    reset_database()