from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.schemas import ScrapeRequest, ScrapeResponse
from core.driver_manager import DriverManager
from core.config import get_emlakjet_config, get_hepsiemlak_config
import logging

# Import scrapers (will need refactoring to import cleanly)
# We will do dynamic imports or ensure the refactor makes them importable
# from scrapers.emlakjet.main import EmlakJetScraper
# from scrapers.hepsiemlak.main import HepsiemlakScraper

router = APIRouter()
logger = logging.getLogger("api")

def run_emlakjet_task(request: ScrapeRequest):
    from scrapers.emlakjet.main import EmlakJetScraper
    
    manager = DriverManager()
    try:
        driver = manager.start()
        config = get_emlakjet_config()
        
        # Construct base URL based on inputs
        # Logic adapted from original main.py
        category_path = config.categories[request.listing_type].get(request.category, '')
        base_url = config.base_url + category_path
        
        # Pass parameters to scraper (Refactor required on Scraper class)
        # Assuming we will refactor the scraper to accept direct options
        scraper = EmlakJetScraper(
            driver=driver,
            base_url=base_url,
            category=request.category,
            # We will add a new init param or method to set simple mode
            # simple_mode=True 
        )
        
        # For now, we need to handle the interactive parts or bypass them.
        # This part assumes the REFACTOR step has been done to add `start_scraping_api` or similar.
        if hasattr(scraper, 'start_scraping_api'):
             scraper.start_scraping_api(
                 cities=request.cities,
                 districts=request.districts,
                 max_pages=request.max_pages
             )
        else:
            logger.warning("Scraper api method not found (Refactor needed)")
            
    except Exception as e:
        logger.error(f"EmlakJet task error: {e}")
    finally:
        manager.stop()

def run_hepsiemlak_task(request: ScrapeRequest):
    from scrapers.hepsiemlak.main import HepsiemlakScraper
    
    manager = DriverManager()
    try:
        driver = manager.start()
        
        scraper = HepsiemlakScraper(
            driver=driver,
            listing_type=request.listing_type,
            category=request.category,
            selected_cities=request.cities
        )
        
        # Similarly, assume refactor allows programmatic run
        if hasattr(scraper, 'start_scraping_api'):
            scraper.start_scraping_api(max_pages=request.max_pages)
        else:
             logger.warning("Scraper api method not found (Refactor needed)")

    except Exception as e:
        logger.error(f"HepsiEmlak task error: {e}")
    finally:
        manager.stop()

@router.post("/scrape/emlakjet", response_model=ScrapeResponse)
async def scrape_emlakjet(request: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_emlakjet_task, request)
    return ScrapeResponse(
        status="accepted",
        message="EmlakJet scraping task started in background",
        data_count=0,
        output_files=[]
    )

@router.post("/scrape/hepsiemlak", response_model=ScrapeResponse)
async def scrape_hepsiemlak(request: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hepsiemlak_task, request)
    return ScrapeResponse(
        status="accepted",
        message="HepsiEmlak scraping task started in background",
        data_count=0,
        output_files=[]
    )
