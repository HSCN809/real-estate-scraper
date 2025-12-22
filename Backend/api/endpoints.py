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
    # Status'u HEMEN ayarla
    task_status.reset()
    task_status.set_running(True)
    task_status.update("EmlakJet taraması başlatılıyor...", progress=0)
    
    background_tasks.add_task(run_emlakjet_task, request)
    return ScrapeResponse(
        status="accepted",
        message="EmlakJet scraping task started in background",
        data_count=0,
        output_files=[]
    )

@router.post("/scrape/hepsiemlak", response_model=ScrapeResponse)
async def scrape_hepsiemlak(request: ScrapeRequest, background_tasks: BackgroundTasks):
    # Status'u HEMEN ayarla - frontend ilk sorguladığında hazır olsun
    task_status.reset()
    task_status.set_running(True)
    task_status.update("HepsiEmlak taraması başlatılıyor...", progress=0)
    
    background_tasks.add_task(run_hepsiemlak_task, request)
    return ScrapeResponse(
        status="accepted",
        message="HepsiEmlak scraping task started in background",
        data_count=0,
        output_files=[]
    )

@router.post("/stop")
async def stop_scraping():
    """Aktif tarama işlemini durdur ve mevcut verileri kaydet"""
    if task_status.is_running:
        task_status.request_stop()
        return {"status": "stopping", "message": "Durdurma isteği gönderildi. Mevcut veriler kaydediliyor..."}
    else:
        return {"status": "idle", "message": "Aktif bir tarama işlemi yok."}

@router.delete("/clear-results")
async def clear_results():
    """Outputs klasöründeki tüm sonuç dosyalarını sil"""
    import os
    import shutil
    
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    output_dir = os.path.join(project_root, "outputs")
    
    if not os.path.exists(output_dir):
        output_dir = os.path.join(project_root, "Outputs")
    
    if not os.path.exists(output_dir):
        return {"status": "error", "message": "Outputs klasörü bulunamadı", "deleted_count": 0}
    
    deleted_count = 0
    try:
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
                deleted_count += 1
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                deleted_count += 1
        
        return {"status": "success", "message": f"{deleted_count} dosya/klasör silindi", "deleted_count": deleted_count}
    except Exception as e:
        return {"status": "error", "message": str(e), "deleted_count": deleted_count}

@router.get("/results")
async def get_results():
    import os
    from datetime import datetime
    
    # Calculate project root robustly
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    # Check for outputs directory
    output_dir = os.path.join(project_root, "outputs")
    if not os.path.exists(output_dir):
        output_dir = os.path.join(project_root, "Outputs")
        if not os.path.exists(output_dir):
            return []

    final_results = []
    
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if filename.lower().endswith(('.xlsx', '.json')):
                file_path = os.path.join(root, filename)
                try:
                    stats = os.stat(file_path)
                    file_size = stats.st_size
                    
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
                    
                    # Listing type detection
                    listing_type = "Satılık" if "satilik" in lower_name else "Kiralık" if "kiralik" in lower_name else "Genel"
                    
                    # City name from filename
                    # Format: hepsiemlak_satilik_konut_afyonkarahisar_20251221_172252.xlsx
                    # Or: hepsiemlak_satilik_konut_balikesir.xlsx (eski format)
                    city = "Bilinmiyor"
                    parts = filename.replace('.xlsx', '').replace('.json', '').split('_')
                    if len(parts) >= 4:
                        # Eğer son parça sayıya benziyorsa (timestamp), 4. pozisyonu al
                        if len(parts) >= 6 and parts[-1].isdigit():
                            city_slug = parts[3]  # hepsiemlak_satilik_konut_SEHIR_...
                        else:
                            city_slug = parts[-1]  # Eski format
                        city = city_slug.replace('-', ' ').title()
                    
                    # Get real record count and average price from Excel file
                    count = 0
                    avg_price = None
                    if filename.endswith('.xlsx'):
                        try:
                            import openpyxl
                            wb = openpyxl.load_workbook(file_path, read_only=True)
                            ws = wb.active
                            count = ws.max_row - 1 if ws.max_row else 0  # Subtract header
                            
                            # Find price column (Fiyat)
                            price_col_idx = None
                            headers = []
                            for idx, cell in enumerate(ws[1]):
                                headers.append(cell.value if cell.value else "")
                                if cell.value and "fiyat" in str(cell.value).lower():
                                    price_col_idx = idx
                            
                            # Calculate average price
                            if price_col_idx is not None:
                                prices = []
                                for row in ws.iter_rows(min_row=2, max_row=min(1000, ws.max_row)):
                                    cell = row[price_col_idx]
                                    if cell.value:
                                        try:
                                            # Remove non-numeric chars and convert
                                            price_str = str(cell.value).replace('.', '').replace(',', '.').replace('TL', '').replace('₺', '').strip()
                                            price = float(price_str)
                                            if price > 0:
                                                prices.append(price)
                                        except:
                                            pass
                                if prices:
                                    avg_price = int(sum(prices) / len(prices))
                            
                            wb.close()
                        except Exception as e:
                            logger.warning(f"Could not read Excel data: {e}")
                    elif filename.endswith('.json'):
                        try:
                            import json
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                count = len(data) if isinstance(data, list) else 0
                        except:
                            pass
                    
                    final_results.append({
                        "id": filename,
                        "platform": platform,
                        "category": category,
                        "listing_type": listing_type,
                        "city": city,
                        "date": datetime.fromtimestamp(stats.st_mtime).strftime('%d.%m.%Y %H:%M'),
                        "count": count,
                        "avg_price": avg_price,
                        "file_size": file_size,
                        "file_size_mb": round(file_size / (1024 * 1024), 2),
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
    return final_results

@router.get("/results/{filename}/preview")
async def get_result_preview(filename: str, limit: int = 20):
    """Dosyadan ilk N kaydı döndür"""
    import os
    from datetime import datetime
    
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    # Find the file
    output_dir = os.path.join(project_root, "outputs")
    if not os.path.exists(output_dir):
        output_dir = os.path.join(project_root, "Outputs")
    
    file_path = None
    for root, dirs, files in os.walk(output_dir):
        if filename in files:
            file_path = os.path.join(root, filename)
            break
    
    if not file_path or not os.path.exists(file_path):
        return {"error": "Dosya bulunamadı", "data": [], "total": 0}
    
    data = []
    total = 0
    
    try:
        if filename.endswith('.xlsx'):
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True)
            ws = wb.active
            
            # Get headers
            headers = []
            for cell in ws[1]:
                headers.append(cell.value if cell.value else "")
            
            # Get data rows
            total = ws.max_row - 1 if ws.max_row else 0
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=min(limit + 1, ws.max_row)), start=1):
                row_data = {}
                for col_idx, cell in enumerate(row):
                    if col_idx < len(headers):
                        row_data[headers[col_idx]] = cell.value if cell.value else ""
                data.append(row_data)
            
            wb.close()
            
        elif filename.endswith('.json'):
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
                if isinstance(all_data, list):
                    total = len(all_data)
                    data = all_data[:limit]
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return {"error": str(e), "data": [], "total": 0}
    
    return {"data": data, "total": total, "showing": len(data)}

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

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Dosyayı indir"""
    import os
    from fastapi.responses import FileResponse
    
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    # Find the file
    output_dir = os.path.join(project_root, "outputs")
    if not os.path.exists(output_dir):
        output_dir = os.path.join(project_root, "Outputs")
    
    file_path = None
    for root, dirs, files in os.walk(output_dir):
        if filename in files:
            file_path = os.path.join(root, filename)
            break
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    
    # Determine media type
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith('.xlsx') else "application/json"
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )
