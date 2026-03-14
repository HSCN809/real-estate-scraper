# -*- coding: utf-8 -*-
"""Chrome WebDriver yoneticisi."""

import os
import time
import random
import logging
import subprocess
from typing import Optional
from contextlib import contextmanager

# Undetected Chromedriver - bot tespiti için tek seçenek
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

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
    """Chrome WebDriver yaşam döngüsünü yönetir"""

    def __init__(self, headless: Optional[bool] = None, proxy_url: Optional[str] = None):
        self.config = get_config()
        self.headless = headless if headless is not None else self.config.headless
        self.proxy_url = proxy_url
        self.driver = None
        self.wait: Optional[WebDriverWait] = None
        self.user_agent = random.choice(USER_AGENTS)

    def _create_options(self) -> Options:
        """Chrome seçeneklerini oluştur"""
        options = Options()

        # Temel tarayıcı ayarları
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={self.user_agent}")
        options.add_argument("--window-size=1920,1080")
        if self.headless:
            options.add_argument("--headless=new")
        if self.proxy_url:
            options.add_argument(f"--proxy-server={self.proxy_url}")

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
        """Webdriver tespitini gizlemek için JS yamaları uygula"""
        if self.driver:
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.execute_script("""
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US', 'en']});
                """)
            except Exception as e:
                logger.debug(f"Stealth script warning: {e}")

    def _resolve_binary_paths(self) -> tuple[Optional[str], Optional[str]]:
        chrome_path = "/usr/bin/google-chrome"
        chromedriver_path = "/usr/bin/chromedriver"

        if not os.path.exists(chrome_path):
            chrome_path = None
        if not os.path.exists(chromedriver_path):
            chromedriver_path = None

        return chrome_path, chromedriver_path

    def _start_standard_driver(self, options: Options, chrome_path: Optional[str], chromedriver_path: Optional[str]) -> WebDriver:
        if chrome_path:
            options.binary_location = chrome_path
            logger.info(f"Using Chrome at: {chrome_path}")

        service = None
        if chromedriver_path:
            service = Service(executable_path=chromedriver_path)
            logger.info(f"Using ChromeDriver at: {chromedriver_path}")

        if service is not None:
            return webdriver.Chrome(service=service, options=options)
        return webdriver.Chrome(options=options)

    def _start_undetected_driver(self, options: Options, chrome_path: Optional[str], chromedriver_path: Optional[str]) -> WebDriver:
        driver_kwargs = {
            "options": options,
            "headless": self.headless,
            "use_subprocess": True,
            "version_main": 145,
        }

        if chrome_path:
            driver_kwargs["browser_executable_path"] = chrome_path
            logger.info(f"Using Chrome at: {chrome_path}")

        if chromedriver_path:
            driver_kwargs["driver_executable_path"] = chromedriver_path
            logger.info(f"Using ChromeDriver at: {chromedriver_path}")

        return uc.Chrome(**driver_kwargs)

    def start(self) -> WebDriver:
        """Chrome driver başlat."""
        last_error = None

        # Önceki zombie process'leri temizle
        _kill_zombie_chrome()

        for attempt in range(self.config.max_retries):
            try:
                mode_label = "UNDETECTED" if self.config.use_undetected_chromedriver else "STANDARD"
                logger.info(f"🚀 Starting {mode_label} Chrome driver (Attempt {attempt + 1}/{self.config.max_retries})")

                options = self._create_options()
                chrome_path, chromedriver_path = self._resolve_binary_paths()
                if self.config.use_undetected_chromedriver:
                    self.driver = self._start_undetected_driver(options, chrome_path, chromedriver_path)
                else:
                    self.driver = self._start_standard_driver(options, chrome_path, chromedriver_path)

                self._apply_stealth_scripts()
                self.wait = WebDriverWait(self.driver, self.config.element_wait_timeout)

                logger.info(f"✅ {mode_label} Chrome driver activated successfully")
                return self.driver

            except Exception as e:
                last_error = e
                logger.warning(f"Driver start failed: {e}")
                _kill_zombie_chrome()
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)

        raise WebDriverException(f"Chrome driver start failed: {last_error}")

    def stop(self):
        """Driver'ı temizle"""
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

    def restart(self) -> WebDriver:
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

    def ensure_driver(self) -> WebDriver:
        """Driver'ın çalıştığından emin ol, çökmüşse yeniden başlat"""
        if not self.is_alive():
            logger.info("🔄 Driver yeniden başlatılıyor...")
            return self.start()
        return self.driver

    def get_driver(self) -> WebDriver:
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


def create_driver(headless: bool = False) -> WebDriver:
    manager = DriverManager(headless=headless)
    return manager.start()
