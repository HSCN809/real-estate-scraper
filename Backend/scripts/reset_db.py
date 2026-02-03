#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Reset Script - Interaktif Menu
Veritabanindaki verileri yonetmek icin kullanilir.

Kullanim:
    docker-compose exec api python scripts/reset_db.py
"""

import sys
import os

# Backend klasorunu path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine, SessionLocal, DATABASE_URL
from database.models import Base, Listing, Location, ScrapeSession, PriceHistory


def get_table_counts(session) -> dict:
    """Tablo sayilarini al"""
    return {
        'listings': session.query(Listing).count(),
        'locations': session.query(Location).count(),
        'scrape_sessions': session.query(ScrapeSession).count(),
        'price_history': session.query(PriceHistory).count(),
    }


def print_stats(session):
    """Istatistikleri yazdir"""
    counts = get_table_counts(session)
    total = sum(counts.values())

    print("\n" + "=" * 50)
    print("  VERITABANI ISTATISTIKLERI")
    print("=" * 50)
    print(f"  Listings (Ilanlar)     : {counts['listings']:,}")
    print(f"  Locations (Konumlar)   : {counts['locations']:,}")
    print(f"  Scrape Sessions        : {counts['scrape_sessions']:,}")
    print(f"  Price History          : {counts['price_history']:,}")
    print("-" * 50)
    print(f"  TOPLAM                 : {total:,} kayit")
    print("=" * 50)

    return counts


def confirm(message: str) -> bool:
    """Onay al"""
    print(f"\n[!] {message}")
    response = input("    Devam etmek icin 'evet' yazin: ")
    return response.lower() in ('evet', 'e', 'yes', 'y')


def delete_all_data(session):
    """Tum verileri sil"""
    print("\n[*] Tum veriler siliniyor...")

    session.query(PriceHistory).delete()
    print("    [+] price_history temizlendi")

    session.query(Listing).delete()
    print("    [+] listings temizlendi")

    session.query(ScrapeSession).delete()
    print("    [+] scrape_sessions temizlendi")

    session.query(Location).delete()
    print("    [+] locations temizlendi")

    session.commit()
    print("\n[OK] Tum veriler basariyla silindi!")


def delete_listings_only(session):
    """Sadece ilanlari sil"""
    print("\n[*] Ilanlar siliniyor...")

    session.query(PriceHistory).delete()
    print("    [+] price_history temizlendi")

    session.query(Listing).delete()
    print("    [+] listings temizlendi")

    session.commit()
    print("\n[OK] Ilanlar basariyla silindi!")


def delete_sessions_only(session):
    """Sadece scrape session'lari sil"""
    print("\n[*] Scrape session'lar siliniyor...")

    # Once ilanlari sil (foreign key)
    session.query(PriceHistory).delete()
    session.query(Listing).delete()
    session.query(ScrapeSession).delete()
    print("    [+] scrape_sessions temizlendi")
    print("    [+] iliskili listings ve price_history de temizlendi")

    session.commit()
    print("\n[OK] Session'lar basariyla silindi!")


def drop_and_recreate(session):
    """Tablolari sil ve yeniden olustur"""
    print("\n[*] Tablolar siliniyor ve yeniden olusturuluyor...")

    session.close()
    Base.metadata.drop_all(bind=engine)
    print("    [+] Tum tablolar silindi")

    Base.metadata.create_all(bind=engine)
    print("    [+] Tablolar yeniden olusturuldu")

    print("\n[OK] Veritabani sifirlandi!")
    return SessionLocal()  # Yeni session dondur


def show_menu():
    """Menu goster"""
    print("\n" + "=" * 50)
    print("  VERITABANI YONETIM MENUSU")
    print("=" * 50)
    print("  1. Istatistikleri Goster")
    print("  2. Tum Verileri Sil")
    print("  3. Sadece Ilanlari Sil (Listings)")
    print("  4. Sadece Session'lari Sil")
    print("  5. Tablolari Sifirla (Drop & Recreate)")
    print("  6. Cikis")
    print("=" * 50)


def main():
    # Veritabani bilgisi
    print("\n" + "=" * 50)
    print("  DATABASE RESET TOOL")
    print("=" * 50)

    if DATABASE_URL and 'postgresql' in DATABASE_URL:
        db_host = DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'unknown'
        print(f"  Veritabani: PostgreSQL ({db_host})")
    else:
        print("  Veritabani: SQLite (lokal)")

    session = SessionLocal()

    try:
        while True:
            show_menu()

            try:
                choice = input("\n  Seciminiz (1-6): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\n[!] Cikis yapiliyor...")
                break

            if choice == '1':
                print_stats(session)

            elif choice == '2':
                counts = get_table_counts(session)
                total = sum(counts.values())

                if total == 0:
                    print("\n[!] Veritabani zaten bos!")
                    continue

                print_stats(session)

                if confirm(f"Toplam {total:,} kayit silinecek!"):
                    delete_all_data(session)
                else:
                    print("\n[X] Islem iptal edildi.")

            elif choice == '3':
                count = session.query(Listing).count()

                if count == 0:
                    print("\n[!] Silinecek ilan yok!")
                    continue

                if confirm(f"{count:,} ilan silinecek!"):
                    delete_listings_only(session)
                else:
                    print("\n[X] Islem iptal edildi.")

            elif choice == '4':
                count = session.query(ScrapeSession).count()

                if count == 0:
                    print("\n[!] Silinecek session yok!")
                    continue

                if confirm(f"{count:,} session ve iliskili ilanlar silinecek!"):
                    delete_sessions_only(session)
                else:
                    print("\n[X] Islem iptal edildi.")

            elif choice == '5':
                if confirm("TUM TABLOLAR SILINECEK VE YENIDEN OLUSTURULACAK!"):
                    session = drop_and_recreate(session)
                else:
                    print("\n[X] Islem iptal edildi.")

            elif choice == '6':
                print("\n[!] Cikis yapiliyor...")
                break

            else:
                print("\n[X] Gecersiz secim! Lutfen 1-6 arasinda bir sayi girin.")

    except Exception as e:
        print(f"\n[HATA] {e}")
        session.rollback()
        sys.exit(1)

    finally:
        session.close()
        print("\n" + "=" * 50)
        print("  Gule gule!")
        print("=" * 50 + "\n")


if __name__ == '__main__':
    main()
