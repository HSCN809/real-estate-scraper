# -*- coding: utf-8 -*-
"""
Real Estate Scraper - Main Entry Point
Provides unified menu for EmlakJet and HepsiEmlak scrapers
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.driver_manager import DriverManager
from core.config import get_emlakjet_config, get_hepsiemlak_config
from utils.logger import setup_logger, get_logger

logger = get_logger("main")


def show_main_menu():
    """Display main menu and get user choice"""
    print("\n" + "=" * 60)
    print("🏠 EMLAK SCRAPER - ANA MENÜ")
    print("=" * 60)
    print("\n1. 🔵 EmlakJet Scraper")
    print("2. 🟢 HepsiEmlak Scraper")
    print("3. 🚪 Çıkış")
    print("\n" + "-" * 60)
    
    try:
        choice = int(input("\nSeçiminiz (1-3): "))
        return choice
    except ValueError:
        print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
        return None


def run_emlakjet_scraper():
    """Run EmlakJet scraper"""
    from scrapers.emlakjet.main import EmlakJetScraper
    
    print("\n" + "=" * 60)
    print("🔵 EMLAKJET SCRAPER")
    print("=" * 60)
    
    # Listing type selection
    print("\nİlan Tipi Seçin:")
    print("1. Satılık")
    print("2. Kiralık")
    print("3. ↩️ Geri")
    
    try:
        type_choice = int(input("\nSeçiminiz (1-3): "))
        if type_choice == 3:
            return
        
        listing_type = "satilik" if type_choice == 1 else "kiralik"
    except ValueError:
        print("❌ Geçersiz giriş!")
        return
    
    # Category selection
    config = get_emlakjet_config()
    categories = list(config.categories[listing_type].keys())
    
    print("\nKategori Seçin:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat.replace('_', ' ').capitalize()}")
    print(f"{len(categories) + 1}. ↩️ Geri")
    
    try:
        cat_choice = int(input(f"\nSeçiminiz (1-{len(categories) + 1}): "))
        if cat_choice == len(categories) + 1:
            return
        
        if 1 <= cat_choice <= len(categories):
            category = categories[cat_choice - 1]
        else:
            print("❌ Geçersiz seçim!")
            return
    except ValueError:
        print("❌ Geçersiz giriş!")
        return
    
    # Start scraping
    manager = DriverManager()
    
    try:
        driver = manager.start()
        
        base_url = config.base_url + config.categories[listing_type][category]
        scraper = EmlakJetScraper(driver, base_url, category)
        scraper.start_scraping()
        
    except Exception as e:
        logger.error(f"EmlakJet scraper error: {e}")
        print(f"❌ Hata: {e}")
    
    finally:
        manager.stop()


def run_hepsiemlak_scraper():
    """Run HepsiEmlak scraper"""
    from scrapers.hepsiemlak.main import HepsiemlakScraper
    
    print("\n" + "=" * 60)
    print("🟢 HEPSİEMLAK SCRAPER")
    print("=" * 60)
    
    # Listing type selection
    print("\nİlan Tipi Seçin:")
    print("1. Satılık")
    print("2. Kiralık")
    print("3. ↩️ Geri")
    
    try:
        type_choice = int(input("\nSeçiminiz (1-3): "))
        if type_choice == 3:
            return
        
        listing_type = "satilik" if type_choice == 1 else "kiralik"
    except ValueError:
        print("❌ Geçersiz giriş!")
        return
    
    # Category selection
    config = get_hepsiemlak_config()
    categories = list(config.categories[listing_type].keys())
    
    print("\nKategori Seçin:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat.replace('_', ' ').capitalize()}")
    print(f"{len(categories) + 1}. ↩️ Geri")
    
    try:
        cat_choice = int(input(f"\nSeçiminiz (1-{len(categories) + 1}): "))
        if cat_choice == len(categories) + 1:
            return
        
        if 1 <= cat_choice <= len(categories):
            category = categories[cat_choice - 1]
        else:
            print("❌ Geçersiz seçim!")
            return
    except ValueError:
        print("❌ Geçersiz giriş!")
        return
    
    # Start scraping
    manager = DriverManager()
    
    try:
        driver = manager.start()
        
        scraper = HepsiemlakScraper(driver, listing_type, category)
        scraper.start_scraping()
        
    except Exception as e:
        logger.error(f"HepsiEmlak scraper error: {e}")
        print(f"❌ Hata: {e}")
    
    finally:
        manager.stop()


def main():
    """Main entry point"""
    # Setup logging
    setup_logger()
    
    print("\n" + "=" * 60)
    print("    🏠 EMLAK SCRAPER v2.0")
    print("    Refactored & Improved Version")
    print("=" * 60)
    
    while True:
        choice = show_main_menu()
        
        if choice == 1:
            run_emlakjet_scraper()
        elif choice == 2:
            run_hepsiemlak_scraper()
        elif choice == 3:
            print("\n👋 Görüşmek üzere!")
            print("=" * 60)
            break
        else:
            if choice is not None:
                print("❌ Geçersiz seçim! Lütfen 1-3 arasında bir sayı girin.")


if __name__ == "__main__":
    main()
