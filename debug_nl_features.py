from retail_os.scrapers.noel_leeming.scraper import setup_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import time

def debug_html():
    driver = setup_driver(headless=True)
    try:
        url = "https://www.noelleeming.co.nz/p/lenovo-yoga-7i-16-inch-intel-core-ultra-7-155u-16gb-ram-512gb-ssd-windows-11-home-2-in-1-notebook-with-lenovo-digital-pen/N229794.html"
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait like the real scraper
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            print("Found h1")
            
            # Scroll down to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(5)
            
        except Exception as e:
            print(f"Timeout/Error: {e}")
            
        # Save full source
        Path("debug_nl_page.html").write_text(driver.page_source, encoding="utf-8")
        print("Saved debug_nl_page.html")
        print(f"Title: {driver.title}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_html()
