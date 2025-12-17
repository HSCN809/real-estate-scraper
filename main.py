# -*- coding: utf-8 -*-
"""
Real Estate Scraper - Main Entry Point
Provides unified menu for all operations
"""

import sys
import os
import subprocess
import threading

# Add Backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "Backend"))

from Backend.utils.logger import setup_logger, get_logger
from Backend.core.driver_manager import DriverManager
from Backend.core.config import get_emlakjet_config, get_hepsiemlak_config

logger = get_logger("main")


def show_main_menu():
    """Display main menu and get user choice"""
    print("\n" + "=" * 60)
    print("🏠 EMLAK SCRAPER - ANA MENÜ")
    print("=" * 60)
    print("\n1. 🔵 EmlakJet Scraper")
    print("2. 🟢 HepsiEmlak Scraper")
    print("3. 🚀 API Server Başlat")
    print("4. 🌐 Frontend Başlat")
    print("5. 🔄 API + Frontend Başlat")
    print("6. 🚪 Çıkış")
    print("\n" + "-" * 60)
    
    try:
        choice = int(input("\nSeçiminiz (1-6): "))
        return choice
    except ValueError:
        print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
        return None


def run_emlakjet_scraper():
    """Run EmlakJet scraper"""
    from Backend.scrapers.emlakjet.main import EmlakJetScraper
    
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
    from Backend.scrapers.hepsiemlak.main import HepsiemlakScraper
    
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


def run_api_server():
    """Run FastAPI server using Uvicorn"""
    import uvicorn
    
    print("\n" + "=" * 60)
    print("🚀 API SERVER")
    print("=" * 60)
    print("Server başlatılıyor... (Durdurmak için CTRL+C)")
    print("Swagger UI: http://localhost:8000/docs")
    print("-" * 60)
    
    try:
        uvicorn.run("Backend.main:app", host="127.0.0.1", port=8000, reload=True)
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"❌ Server hatası: {e}")


def run_frontend():
    """Run Next.js frontend dev server"""
    print("\n" + "=" * 60)
    print("🌐 FRONTEND SERVER")
    print("=" * 60)
    print("Frontend başlatılıyor... (Durdurmak için CTRL+C)")
    print("URL: http://localhost:3000")
    print("-" * 60)
    
    try:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_dir = os.path.join(root_dir, "Frontend")
        
        subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, shell=True)
    except KeyboardInterrupt:
        print("\n⏹️  Frontend durduruldu.")
    except Exception as e:
        logger.error(f"Frontend error: {e}")
        print(f"❌ Frontend hatası: {e}")


def run_full_stack():
    """Run both API and Frontend servers"""
    print("\n" + "=" * 60)
    print("🔄 FULL STACK MODE")
    print("=" * 60)
    print("API + Frontend başlatılıyor... (Durdurmak için CTRL+C)")
    print("API: http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("-" * 60)
    
    try:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_dir = os.path.join(root_dir, "Frontend")
        
        # Start Frontend in a separate thread
        def start_frontend():
            subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, shell=True)
        
        frontend_thread = threading.Thread(target=start_frontend, daemon=True)
        frontend_thread.start()
        
        # Start API in main thread
        import uvicorn
        uvicorn.run("Backend.main:app", host="127.0.0.1", port=8000, reload=True)
        
    except KeyboardInterrupt:
        print("\n⏹️  Sunucular durduruldu.")
    except Exception as e:
        logger.error(f"Full stack error: {e}")
        print(f"❌ Hata: {e}")


def main():
    """Main entry point"""
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
            run_api_server()
        elif choice == 4:
            run_frontend()
        elif choice == 5:
            run_full_stack()
        elif choice == 6:
            print("\n👋 Görüşmek üzere!")
            print("=" * 60)
            break
        else:
            if choice is not None:
                print("❌ Geçersiz seçim! Lütfen 1-6 arasında bir sayı girin.")


if __name__ == "__main__":
    main()
