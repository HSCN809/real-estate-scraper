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
        
        # DEBUG: Log received parameters
        print(f"DEBUG API: listing_type={request.listing_type}, category={request.category}, cities={request.cities}")
        
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

@router.get("/analytics/prices")
async def get_price_analytics(
    platform: str = None,
    category: str = None,
    listing_type: str = None
):
    """Tüm dosyalardan fiyat verilerini çek - grafikler için (filtrelenebilir)"""
    import os
    import re
    
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    output_dir = os.path.join(project_root, "outputs")
    if not os.path.exists(output_dir):
        output_dir = os.path.join(project_root, "Outputs")
    
    if not os.path.exists(output_dir):
        return {"prices": [], "summary": {"total_count": 0}}
    
    all_prices = []
    
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if not filename.lower().endswith('.xlsx'):
                continue
                
            file_path = os.path.join(root, filename)
            lower_name = filename.lower()
            
            # Metadata extraction
            file_platform = "HepsiEmlak" if "hepsiemlak" in lower_name else "Emlakjet" if "emlakjet" in lower_name else "Unknown"
            file_category = "Konut" if "konut" in lower_name else "Arsa" if "arsa" in lower_name else "İşyeri" if "isyeri" in lower_name else "Genel"
            file_listing_type = "Satılık" if "satilik" in lower_name else "Kiralık" if "kiralik" in lower_name else "Genel"
            
            # Apply filters - skip files that don't match
            if platform and platform != "all" and file_platform != platform:
                continue
            if category and category != "all" and file_category != category:
                continue
            if listing_type and listing_type != "all" and file_listing_type != listing_type:
                continue
            
            # City extraction
            parts = filename.replace('.xlsx', '').split('_')
            city = "Bilinmiyor"
            if len(parts) >= 4:
                if len(parts) >= 6 and parts[-1].isdigit():
                    city = parts[3].replace('-', ' ').title()
                else:
                    city = parts[-1].replace('-', ' ').title()
            
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True)
                ws = wb.active
                
                # Find price column
                price_col_idx = None
                header_row = next(ws.iter_rows(min_row=1, max_row=1))
                
                for idx, cell in enumerate(header_row):
                    val = str(cell.value).strip().lower() if cell.value else ""
                    if val == "fiyat":
                        price_col_idx = idx
                        break
                    elif "fiyat" in val and "metrekare" not in val:
                        if price_col_idx is None:
                            price_col_idx = idx
                
                if price_col_idx is not None:
                    for row in ws.iter_rows(min_row=2):
                        cell = row[price_col_idx]
                        if cell.value:
                            try:
                                val_str = str(cell.value).strip()
                                val_str = re.sub(r'\s+', '', val_str)
                                val_str = val_str.replace('TL', '').replace('₺', '')
                                
                                if ',' in val_str and '.' in val_str:
                                    val_str = val_str.replace('.', '').replace(',', '.')
                                elif '.' in val_str and val_str.count('.') > 1:
                                    val_str = val_str.replace('.', '')
                                elif '.' in val_str and len(val_str.split('.')[-1]) == 3:
                                    val_str = val_str.replace('.', '')
                                elif ',' in val_str:
                                    val_str = val_str.replace(',', '.')
                                
                                price = float(val_str)
                                if price > 0:
                                    all_prices.append({
                                        "city": city,
                                        "platform": file_platform,
                                        "category": file_category,
                                        "listing_type": file_listing_type,
                                        "price": price
                                    })
                            except:
                                pass
                
                wb.close()
            except Exception as e:
                logger.warning(f"Could not read prices from {filename}: {e}")
    
    # Summary stats
    summary = {
        "total_count": len(all_prices),
        "avg_price": round(sum(p["price"] for p in all_prices) / len(all_prices), 2) if all_prices else 0,
        "min_price": min(p["price"] for p in all_prices) if all_prices else 0,
        "max_price": max(p["price"] for p in all_prices) if all_prices else 0
    }
    
    return {"prices": all_prices, "summary": summary}

@router.get("/analytics/file-stats/{filename}")
async def get_file_statistics(filename: str):
    """Dosya bazlı detaylı istatistikler - describe + fiyat aralıkları"""
    import os
    import re
    import statistics
    
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    output_dir = os.path.join(project_root, "outputs")
    if not os.path.exists(output_dir):
        output_dir = os.path.join(project_root, "Outputs")
    
    # Find the file
    file_path = None
    for root, dirs, files in os.walk(output_dir):
        if filename in files:
            file_path = os.path.join(root, filename)
            break
    
    if not file_path or not os.path.exists(file_path):
        return {"error": "Dosya bulunamadı", "stats": None}
    
    prices = []
    
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True)
        ws = wb.active
        
        # Find price column
        price_col_idx = None
        header_row = next(ws.iter_rows(min_row=1, max_row=1))
        
        for idx, cell in enumerate(header_row):
            val = str(cell.value).strip().lower() if cell.value else ""
            if val == "fiyat":
                price_col_idx = idx
                break
            elif "fiyat" in val and "metrekare" not in val:
                if price_col_idx is None:
                    price_col_idx = idx
        
        if price_col_idx is not None:
            for row in ws.iter_rows(min_row=2):
                cell = row[price_col_idx]
                if cell.value:
                    try:
                        val_str = str(cell.value).strip()
                        val_str = re.sub(r'\s+', '', val_str)
                        val_str = val_str.replace('TL', '').replace('₺', '')
                        
                        if ',' in val_str and '.' in val_str:
                            val_str = val_str.replace('.', '').replace(',', '.')
                        elif '.' in val_str and val_str.count('.') > 1:
                            val_str = val_str.replace('.', '')
                        elif '.' in val_str and len(val_str.split('.')[-1]) == 3:
                            val_str = val_str.replace('.', '')
                        elif ',' in val_str:
                            val_str = val_str.replace(',', '.')
                        
                        price = float(val_str)
                        if price > 0:
                            prices.append(price)
                    except:
                        pass
        
        wb.close()
    except Exception as e:
        logger.error(f"Error reading file stats: {e}")
        return {"error": str(e), "stats": None}
    
    if not prices:
        return {"error": "Fiyat verisi bulunamadı", "stats": None}
    
    # Sort prices for percentile calculations
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    
    # Calculate percentiles (quartiles)
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f) if c < len(data) else data[f]
    
    # Descriptive statistics (like pandas describe)
    describe_stats = {
        "count": n,
        "mean": round(statistics.mean(prices), 2),
        "std": round(statistics.stdev(prices), 2) if n > 1 else 0,
        "min": round(min(prices), 2),
        "q25": round(percentile(sorted_prices, 25), 2),
        "median": round(statistics.median(prices), 2),
        "q75": round(percentile(sorted_prices, 75), 2),
        "max": round(max(prices), 2)
    }
    
    # Dynamic price range distribution using quantile-based binning (like pandas qcut)
    # Create 5 bins based on data distribution
    num_bins = 5
    bin_edges = [percentile(sorted_prices, i * 100 / num_bins) for i in range(num_bins + 1)]
    
    # Ensure unique edges
    unique_edges = []
    for e in bin_edges:
        if not unique_edges or e > unique_edges[-1]:
            unique_edges.append(e)
    
    # If not enough unique edges, fall back to equal-width bins
    if len(unique_edges) < 3:
        min_p, max_p = min(prices), max(prices)
        bin_width = (max_p - min_p) / num_bins
        unique_edges = [min_p + i * bin_width for i in range(num_bins + 1)]
    
    # Count items in each bin
    price_ranges = []
    for i in range(len(unique_edges) - 1):
        low = unique_edges[i]
        high = unique_edges[i + 1]
        
        # Format the range label
        def format_price(p):
            if p >= 1000000:
                return f"{p/1000000:.1f}M"
            elif p >= 1000:
                return f"{p/1000:.0f}K"
            else:
                return f"{p:.0f}"
        
        label = f"{format_price(low)} - {format_price(high)}"
        
        # Count items in range
        if i == len(unique_edges) - 2:  # Last bin includes upper edge
            count = sum(1 for p in prices if low <= p <= high)
        else:
            count = sum(1 for p in prices if low <= p < high)
        
        price_ranges.append({
            "range": label,
            "count": count,
            "percentage": round(count / n * 100, 1)
        })
    
    return {
        "stats": describe_stats,
        "price_ranges": price_ranges,
        "total_listings": n
    }

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
                            # Find price column (Fiyat)
                            price_col_idx = None
                            headers = []
                            # Use iter_rows for header to be safe in read_only
                            header_row = next(ws.iter_rows(min_row=1, max_row=1))
                            
                            for idx, cell in enumerate(header_row):
                                val = str(cell.value).strip() if cell.value else ""
                                headers.append(val)
                                val_lower = val.lower()
                                # Priority 1: Exact "fiyat"
                                if val_lower == "fiyat":
                                    price_col_idx = idx
                                    break # Found exact match, stop searching
                                # Priority 2: Contains "fiyat" but NOT "metrekare" (if no exact match found yet)
                                elif "fiyat" in val_lower and "metrekare" not in val_lower:
                                    if price_col_idx is None: # Only set if not set already
                                        price_col_idx = idx

                            # Calculate average price
                            if price_col_idx is not None:
                                prices = []
                                # Iterate all rows (starting from row 2)
                                for row in ws.iter_rows(min_row=2):
                                    cell = row[price_col_idx]
                                    if cell.value:
                                        try:
                                            # Robust price cleaning
                                            import re
                                            val_str = str(cell.value).strip()
                                            # Remove all whitespace (including \xa0) and currency symbols
                                            val_str = re.sub(r'\s+', '', val_str)
                                            val_str = val_str.replace('TL', '').replace('₺', '')
                                            
                                            # Handle 1.234,56 format -> 1234.56
                                            if ',' in val_str and '.' in val_str:
                                                val_str = val_str.replace('.', '').replace(',', '.')
                                            elif '.' in val_str and val_str.count('.') > 1: 
                                                # Multiple dots like 1.234.567 -> 1234567
                                                val_str = val_str.replace('.', '')
                                            elif '.' in val_str and len(val_str.split('.')[-1]) == 3:
                                                # Likely thousands separator 45.000 -> 45000
                                                val_str = val_str.replace('.', '')
                                            elif ',' in val_str:
                                                # Likely decimal separator or thousands (ambiguous, assume decimal if at end?)
                                                # In TR, comma is decimal. 15,5 -> 15.5
                                                val_str = val_str.replace(',', '.')
                                            
                                            price = float(val_str)
                                            if price > 0:
                                                prices.append(price)
                                        except Exception:
                                            pass
                                
                                if prices:
                                    avg_price = round(sum(prices) / len(prices), 2)
                            
                            wb.close()
                        except Exception as e:
                            logger.warning(f"Could not read Excel data for {filename}: {e}")
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
