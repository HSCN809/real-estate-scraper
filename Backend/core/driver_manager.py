# -*- coding: utf-8 -*-
"""
Chrome WebDriver Manager - PURE STEALTH MODE
Exclusively uses undetected-chromedriver to bypass bot detection.
Optimized for Docker container environment.
"""

import os
import time
import random
import logging
import subprocess
from typing import Optional
from contextlib import contextmanager

# Undetected Chromedriver - bot tespiti için tek seçenek
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException

from .config import get_config

logger = logging.getLogger(__name__)

# User-Agent havuzu
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def _kill_zombie_chrome():
    """Önceki Chrome/chromedriver process'lerini temizle"""
    try:
        subprocess.run(["pkill", "-f", "chrome"], capture_output=True, timeout=5)
        subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True, timeout=5)
        time.sleep(1)
    except Exception:
        pass


class DriverManager:
    """
    Manages Chrome WebDriver lifecycle using ONLY undetected-chromedriver.
    Optimized for Docker/container environments.
    """

    def __init__(self, headless: Optional[bool] = None):
        self.config = get_config()
        self.headless = headless if headless is not None else self.config.headless
        self.driver = None
        self.wait: Optional[WebDriverWait] = None
        self.user_agent = random.choice(USER_AGENTS)

    def _create_options(self) -> uc.ChromeOptions:
        """Create Chrome options for undetected-chromedriver"""
        options = uc.ChromeOptions()

        # Temel ayarlar
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={self.user_agent}")
        options.add_argument("--window-size=1920,1080")

        # Docker/container ortamı için kritik ayarlar
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--safebrowsing-disable-auto-update")

        # Remote debugging port (undetected_chromedriver bunu kullanır)
        options.add_argument("--remote-debugging-port=0")

        # Gereksiz logging'leri kapat
        options.add_argument("--log-level=3")
        options.add_argument("--silent")

        # Resimleri kapat (Hız için)
        if self.config.disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)

        return options

    def _apply_stealth_scripts(self):
        """Webdriver olduğunu gizlemek için JS patch'leri"""
        if self.driver:
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.execute_script("""
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US', 'en']});
                """)
            except Exception as e:
                logger.debug(f"Stealth script warning: {e}")

    def start(self) -> uc.Chrome:
        """Starts purely in undetected mode"""
        last_error = None

        # Önceki zombie process'leri temizle
        _kill_zombie_chrome()

        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🚀 Starting UNDETECTED Chrome driver (Attempt {attempt + 1}/{self.config.max_retries})")

                options = self._create_options()

                # Docker ortamında önceden kurulu Chrome ve ChromeDriver kullan
                chrome_path = "/usr/bin/google-chrome"
                chromedriver_path = "/usr/bin/chromedriver"

                # Windows/local için farklı path kontrol et
                if not os.path.exists(chrome_path):
                    chrome_path = None  # undetected_chromedriver kendi bulacak
                    chromedriver_path = None

                driver_kwargs = {
                    "options": options,
                    "headless": self.headless,
                    "use_subprocess": True,
                    "version_main": 145,  # Chrome for Testing version
                }

                if chrome_path and os.path.exists(chrome_path):
                    driver_kwargs["browser_executable_path"] = chrome_path
                    logger.info(f"Using Chrome at: {chrome_path}")

                if chromedriver_path and os.path.exists(chromedriver_path):
                    driver_kwargs["driver_executable_path"] = chromedriver_path
                    logger.info(f"Using ChromeDriver at: {chromedriver_path}")

                self.driver = uc.Chrome(**driver_kwargs)

                self._apply_stealth_scripts()
                self.wait = WebDriverWait(self.driver, self.config.element_wait_timeout)

                logger.info("✅ UNDETECTED mode activated successfully")
                return self.driver

            except Exception as e:
                last_error = e
                logger.warning(f"Driver start failed: {e}")
                _kill_zombie_chrome()
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)

        raise WebDriverException(f"Pure stealth mode failed: {last_error}")

    def stop(self):
        """Cleanup driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver gracefully stopped")
            except OSError:
                pass
            except Exception as e:
                logger.debug(f"Driver stop warning: {e}")
            finally:
                self.driver = None
                self.wait = None

    def restart(self) -> uc.Chrome:
        self.stop()
        return self.start()

    def is_alive(self) -> bool:
        """Driver'ın hala çalışıp çalışmadığını kontrol et"""
        if self.driver is None:
            return False
        try:
            _ = self.driver.current_url
            return True
        except:
            logger.warning("⚠️ Driver çökmüş, yeniden başlatılması gerekiyor!")
            self.driver = None
            self.wait = None
            return False

    def ensure_driver(self) -> uc.Chrome:
        """Driver'ın çalıştığından emin ol, çökmüşse yeniden başlat"""
        if not self.is_alive():
            logger.info("🔄 Driver yeniden başlatılıyor...")
            return self.start()
        return self.driver

    def get_driver(self) -> uc.Chrome:
        return self.ensure_driver()

    def get_wait(self) -> WebDriverWait:
        if self.wait is None:
            self.ensure_driver()
        return self.wait

    def navigate(self, url: str, wait_time: Optional[float] = None) -> bool:
        try:
            wait = wait_time or 2.0
            driver = self.get_driver()
            driver.get(url)
            time.sleep(wait)
            return True
        except Exception as e:
            logger.error(f"Navigation failed to {url}: {e}")
            return False

    @contextmanager
    def session(self):
        try:
            yield self.start()
        finally:
            self.stop()

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


def create_driver(headless: bool = False) -> uc.Chrome:
    manager = DriverManager(headless=headless)
    return manager.start()
