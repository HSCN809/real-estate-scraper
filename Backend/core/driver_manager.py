# -*- coding: utf-8 -*-
"""
Chrome WebDriver Manager with STEALTH anti-detection features and retry mechanism
Uses undetected-chromedriver to bypass Cloudflare, bot detection, etc.
"""

import time
import random
import logging
from typing import Optional
from contextlib import contextmanager

# Selenium import - her durumda gerekli (type annotations için)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Stealth driver - bypasses most bot detection
try:
    import undetected_chromedriver as uc
    USE_UNDETECTED = True
except ImportError:
    USE_UNDETECTED = False
    logging.warning("undetected-chromedriver not installed. Using standard Selenium. Run: pip install undetected-chromedriver")

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException

from .config import get_config

logger = logging.getLogger(__name__)

# User-Agent havuzu - her seferinde farklı bir tarayıcı gibi görünmek için
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


class DriverManager:
    """
    Manages Chrome WebDriver lifecycle with STEALTH anti-detection features.
    Uses undetected-chromedriver to bypass Cloudflare, Turnstile, and bot detection.
    """
    
    def __init__(self, headless: Optional[bool] = None):
        """
        Initialize DriverManager.
        
        Args:
            headless: Override config headless setting. If None, uses config value.
        """
        self.config = get_config()
        self.headless = headless if headless is not None else self.config.headless
        self.driver = None
        self.wait: Optional[WebDriverWait] = None
        # Rastgele User-Agent seç
        self.user_agent = random.choice(USER_AGENTS)
    
    def _create_stealth_options(self):
        """Create stealth Chrome options for undetected-chromedriver"""
        options = uc.ChromeOptions() if USE_UNDETECTED else Options()
        
        # Temel ayarlar
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Rastgele User-Agent
        options.add_argument(f"user-agent={self.user_agent}")
        
        # Pencere boyutu (headless modda da gerekli)
        options.add_argument("--window-size=1920,1080")
        
        # Logging kapatma
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        
        # Resimleri devre dışı bırak (hız için)
        if self.config.disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
        
        return options
    
    def _apply_extra_stealth(self):
        """Apply additional stealth JavaScript patches"""
        if self.driver:
            # WebDriver property'sini gizle
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            # Plugins ve languages ekle (boş olması bot işareti)
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['tr-TR', 'tr', 'en-US', 'en']
                });
            """)
    
    def start(self):
        """
        Start the Chrome driver with STEALTH mode.
        Uses undetected-chromedriver if available, falls back to standard Selenium.
        
        Returns:
            Chrome WebDriver instance
            
        Raises:
            WebDriverException: If driver fails to start after all retries
        """
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🚀 Starting STEALTH Chrome driver (attempt {attempt + 1}/{self.config.max_retries})")
                logger.info(f"   User-Agent: {self.user_agent[:50]}...")
                
                options = self._create_stealth_options()
                
                if USE_UNDETECTED:
                    # Undetected ChromeDriver - Cloudflare, Turnstile bypass
                    self.driver = uc.Chrome(
                        options=options,
                        headless=self.headless,
                        use_subprocess=True,
                        version_main=None  # Otomatik Chrome versiyonu algılama
                    )
                    logger.info("✅ Using undetected-chromedriver (STEALTH MODE)")
                else:
                    # Fallback: Standart Selenium
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options as SeleniumOptions
                    
                    chrome_options = SeleniumOptions()
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_argument(f"user-agent={self.user_agent}")
                    
                    if self.headless:
                        chrome_options.add_argument("--headless=new")
                    
                    self.driver = webdriver.Chrome(options=chrome_options)
                    logger.warning("⚠️ Using standard Selenium (install undetected-chromedriver for better stealth)")
                
                # Ekstra stealth JavaScript patch'leri uygula
                self._apply_extra_stealth()
                
                # Create wait object
                self.wait = WebDriverWait(self.driver, self.config.element_wait_timeout)
                
                logger.info("Chrome driver started successfully")
                return self.driver
                
            except WebDriverException as e:
                last_error = e
                logger.warning(f"Failed to start driver (attempt {attempt + 1}): {e}")
                
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (self.config.retry_multiplier ** attempt)
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
        
        raise WebDriverException(f"Failed to start Chrome driver after {self.config.max_retries} attempts: {last_error}")
    
    def stop(self):
        """Stop the Chrome driver and clean up"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome driver stopped")
            except Exception as e:
                logger.warning(f"Error stopping driver: {e}")
            finally:
                self.driver = None
                self.wait = None
    
    def restart(self) -> webdriver.Chrome:
        """Restart the Chrome driver"""
        self.stop()
        return self.start()
    
    def get_driver(self) -> webdriver.Chrome:
        """Get the current driver, starting if necessary"""
        if self.driver is None:
            return self.start()
        return self.driver
    
    def get_wait(self) -> WebDriverWait:
        """Get the WebDriverWait object"""
        if self.wait is None:
            self.get_driver()
        return self.wait
    
    def navigate(self, url: str, wait_time: float = 2.0) -> bool:
        """
        Navigate to a URL with error handling.
        
        Args:
            url: URL to navigate to
            wait_time: Time to wait after navigation
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            driver = self.get_driver()
            driver.get(url)
            time.sleep(wait_time)
            logger.info(f"Navigated to: {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return False
    
    @contextmanager
    def session(self):
        """
        Context manager for driver session.
        
        Usage:
            with driver_manager.session() as driver:
                driver.get("https://example.com")
        """
        try:
            yield self.start()
        finally:
            self.stop()
    
    def __enter__(self):
        """Enter context manager"""
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        self.stop()
        return False


def create_driver(headless: bool = False) -> webdriver.Chrome:
    """
    Convenience function to create a Chrome driver with anti-detection.
    
    Args:
        headless: Whether to run in headless mode
        
    Returns:
        Chrome WebDriver instance
    """
    manager = DriverManager(headless=headless)
    return manager.start()
