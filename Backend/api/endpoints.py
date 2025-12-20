from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.schemas import ScrapeRequest, ScrapeResponse
from core.driver_manager import DriverManager
from core.config import get_emlakjet_config, get_hepsiemlak_config
from api.status import task_status
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
        
        # Reset and start status
        task_status.reset()
        task_status.set_running(True)
        task_status.update("EmlakJet scraper başlatılıyor...", progress=0)

        def progress_callback(message, current=0, total=0, progress=0):
            task_status.update(message=message, current=current, total=total, progress=progress)
        
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
                 max_pages=request.max_pages,
                 progress_callback=progress_callback
             )
        else:
            logger.warning("Scraper api method not found (Refactor needed)")
            
    except Exception as e:
        logger.error(f"EmlakJet task error: {e}")
    finally:
        task_status.set_running(False)
        task_status.update("İşlem tamamlandı", progress=100)
        manager.stop()

def run_hepsiemlak_task(request: ScrapeRequest):
    from scrapers.hepsiemlak.main import HepsiemlakScraper
    
    manager = DriverManager()
    try:
        driver = manager.start()
        
        # Reset and start status
        task_status.reset()
        task_status.set_running(True)
        task_status.update("HepsiEmlak scraper başlatılıyor...", progress=0)
        
        def progress_callback(message, current=0, total=0, progress=0):
            task_status.update(message=message, current=current, total=total, progress=progress)
        
        scraper = HepsiemlakScraper(
            driver=driver,
            listing_type=request.listing_type,
            category=request.category,
            selected_cities=request.cities
        )
        
        # Similarly, assume refactor allows programmatic run
        if hasattr(scraper, 'start_scraping_api'):
            scraper.start_scraping_api(max_pages=request.max_pages, progress_callback=progress_callback)
        else:
             logger.warning("Scraper api method not found (Refactor needed)")

    except Exception as e:
        logger.error(f"HepsiEmlak task error: {e}")
    finally:
        task_status.set_running(False)
        task_status.update("İşlem tamamlandı", progress=100)
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

@router.get("/results")
async def get_results():
    import os
    from datetime import datetime
    
    # Calculate project root robustly
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    # Check for outputs directory (trying both cases just to be safe, though Windows is insensitive)
    output_dir_name = "outputs"
    output_dir = os.path.join(project_root, output_dir_name)
    
    if not os.path.exists(output_dir):
        # Try capitalized
        output_dir = os.path.join(project_root, "Outputs")
        if not os.path.exists(output_dir):
            logger.warning(f"Output directory not found at {os.path.join(project_root, 'outputs')} or Outputs")
            return []

    final_results = []
    
    print(f"DEBUG: Scanning directory for results: {output_dir}")
    
    # Use os.walk for robust directory traversal
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if filename.lower().endswith(('.xlsx', '.json')):
                file_path = os.path.join(root, filename)
                try:
                    stats = os.stat(file_path)
                    
                    # Platform detection
                    platform = "Unknown"
                    lower_name = filename.lower()
                    if "emlakjet" in lower_name: 
                        platform = "Emlakjet" 
                    elif "hepsiemlak" in lower_name: 
                        platform = "HepsiEmlak"
                    
                    # Category detection
                    category = "Genel"
                    if "konut" in lower_name: category = "Konut"
                    elif "arsa" in lower_name: category = "Arsa"
                    elif "isyeri" in lower_name: category = "İşyeri"
                    
                    final_results.append({
                        "id": filename,
                        "platform": platform,
                        "category": category,
                        "date": datetime.fromtimestamp(stats.st_mtime).strftime('%d.%m.%Y %H:%M'),
                        "count": 0, 
                        "status": "completed",
                        "files": [{
                            "type": "excel" if filename.endswith('.xlsx') else "json",
                            "name": filename,
                            "path": file_path
                        }]
                    })
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
        
    # Sort by date descending
    final_results.sort(key=lambda x: x['date'], reverse=True)
    print(f"DEBUG: Found {len(final_results)} results")
    return final_results

@router.get("/status")
async def get_status():
    return task_status.to_dict()

@router.get("/stats")
async def get_stats():
    import os
    from datetime import datetime, timedelta
    
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    output_dir = os.path.join(project_root, "outputs")
    if not os.path.exists(output_dir):
        output_dir = os.path.join(project_root, "Outputs")

    total_scrapes = 0
    total_listings = 0
    
    this_week_count = 0
    this_month_count = 0
    last_scrape_date = "-"
    
    if os.path.exists(output_dir):
        files = []
        for root, dirs, project_files in os.walk(output_dir):
            for filename in project_files:
                if filename.lower().endswith(('.xlsx', '.json')):
                    files.append(os.path.join(root, filename))
            
        total_scrapes = len(files)
        
        # Sort files by time for recent activity
        files.sort(key=os.path.getmtime, reverse=True)
        
        if files:
            last_scrape_ts = os.path.getmtime(files[0])
            last_scrape_date = datetime.fromtimestamp(last_scrape_ts).strftime('%d.%m.%Y %H:%M')

        now = datetime.now()
        for f in files:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(f))
                if now - mtime < timedelta(days=7):
                    this_week_count += 1
                if now - mtime < timedelta(days=30):
                    this_month_count += 1
            except OSError:
                continue
                
    return {
        "total_scrapes": total_scrapes,
        "total_listings": 0,
        "this_week": this_week_count,
        "this_month": this_month_count,
        "last_scrape": last_scrape_date
    }


