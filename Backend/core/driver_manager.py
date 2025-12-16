# -*- coding: utf-8 -*-
"""
Chrome WebDriver Manager with anti-detection features and retry mechanism
"""

import time
import logging
from typing import Optional
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException

from .config import get_config

logger = logging.getLogger(__name__)


class DriverManager:
    """
    Manages Chrome WebDriver lifecycle with anti-detection features.
    Implements retry mechanism and proper cleanup.
    """
    
    def __init__(self, headless: Optional[bool] = None):
        """
        Initialize DriverManager.
        
        Args:
            headless: Override config headless setting. If None, uses config value.
        """
        self.config = get_config()
        self.headless = headless if headless is not None else self.config.headless
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
    
    def _create_options(self) -> Options:
        """Create Chrome options with anti-detection settings"""
        chrome_options = Options()
        
        # Basic settings
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Anti-detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Disable logging
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-dev-tools")
        
        # User agent
        chrome_options.add_argument(f"user-agent={self.config.user_agent}")
        
        # Headless mode
        if self.headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--window-size=1920,1080")
        
        # Disable images (optional, for faster loading)
        if self.config.disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)
        
        return chrome_options
    
    def _apply_anti_detection(self):
        """Apply anti-detection JavaScript"""
        if self.driver:
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
    
    def start(self) -> webdriver.Chrome:
        """
        Start the Chrome driver with retry mechanism.
        
        Returns:
            Chrome WebDriver instance
            
        Raises:
            WebDriverException: If driver fails to start after all retries
        """
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Starting Chrome driver (attempt {attempt + 1}/{self.config.max_retries})")
                
                options = self._create_options()
                self.driver = webdriver.Chrome(options=options)
                
                # Apply anti-detection
                self._apply_anti_detection()
                
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
