# scraper.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import tempfile
import time
import logging
import pandas as pd
import os
import re

# Logging setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())

def open_browser(link):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # ✅ Use a temporary user data directory
    temp_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(link)
    time.sleep(3)
    return driver

def type_search_query(driver, search):
    try:
        search_box = driver.find_element(By.XPATH, '//*[@id="APjFqb"]')
        search_box.clear()
        search_box.send_keys(search)
        search_box.send_keys(webdriver.common.keys.Keys.RETURN)
        logging.info(f"Typed search query: {search}")
        return driver
    except Exception as e:
        logging.error(f"Error typing query: {e}")
        return driver

def find_info(search, html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for container in soup.select("a.rllt__link"):
            try:
                name_elem = container.select_one("div.dbg0pd span.OSrXXb")
                name = name_elem.get_text(strip=True) if name_elem else None
                details_div = container.select_one("div.rllt__details")
                if not details_div:
                    continue

                address, contact_number = None, None
                info = []

                for div in details_div.find_all("div", recursive=False):
                    text = div.get_text(strip=True)
                    info.append(text)
                    if re.search(r'\+[\d\s\-()]+', text):
                        contact_number = re.search(r'\+[\d\s\-()]+', text).group(0)
                    elif ',' in text and not any(x in text.lower() for x in ['closed', 'opens']):
                        address = text
                timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
                current_date = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()

                results.append({
                    "search": search,
                    "name": name,
                    "address": address,
                    "contact_number": contact_number,
                    "info": "\n".join(info),
                    "Date": current_date,
                    "timestamp": timestamp
                })

            except Exception as e:
                continue
        return results
    except Exception as e:
        logging.error(f"Scraping error: {e}")
        return []
    
def click_next(driver):
    try:
        wait = WebDriverWait(driver, 5)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Next' or text()='التالي']/parent::a")))
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(3)
        logging.info("Clicked next button. Waiting for page to load...")
        return True
    except Exception as e:
        logging.warning("Next button not found or not clickable. Reached last page.")
        return False

def save_to_excel(data, filename="saller_info_new_web.xlsx"):
    df_new = pd.DataFrame(data)
    if os.path.exists(filename):
        df_existing = pd.read_excel(filename)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_excel(filename, index=False)
    logging.info(f"Saved {len(data)} records to {filename}.")

def scrape_google_places(search_query):
    try:
        url = "https://www.google.com/search?q=dress+shop+in+california&sca_esv=2b90c4446a66ec78&hl=en&biw=1536&bih=695&tbm=lcl&ei=j4N7aJyAG-qzvr0P5J2OqQM&ved=0ahUKEwjcg87h6siOAxXqma8BHeSOIzUQ4dUDCAo&uact=5&oq=dress+shop+in+california&gs_lp=Eg1nd3Mtd2l6LWxvY2FsIhhkcmVzcyBzaG9wIGluIGNhbGlmb3JuaWEyBhAAGBYYHjIGEAAYFhgeMgYQABgWGB4yBhAAGBYYHjIGEAAYFhgeMgYQABgWGB4yBhAAGBYYHjIGEAAYFhgeMgYQABgWGB4yBhAAGBYYHkj5OVDaBliJM3ABeACQAQCYAcABoAHBF6oBBDAuMTm4AQPIAQD4AQGYAhOgAvEWwgIFECEYoAHCAgQQIRgVwgIFECEYnwXCAgsQABiABBiGAxiKBcICCBAAGIAEGKIEwgIFEAAY7wXCAgUQABiABMICCxAAGIAEGJECGIoFmAMAiAYBkgcEMS4xOKAHoo0BsgcEMC4xOLgH6RbCBwQyLTE5yAda&sclient=gws-wiz-local#rlfi=hd:;si:;mv:[[38.465075899999995,-116.79096260000001],[32.27355,-122.25069130000001]];tbs:lrf:!1m4!1u3!2m2!3m1!1e1!1m4!1u2!2m2!2m1!1e1!2m1!1e2!2m1!1e3!3sIAE,lf:1,lf_ui:10"
        driver = open_browser(url)
        # driver = click_on_search_result(driver)
        logging.info("Starting to scrape data...")
        # time.sleep(5)  # Wait for the page to load after clicking
        driver = type_search_query(driver, search_query)
        time.sleep(5)  # Wait for the search results to load

        for i in range(50):  # Adjust the range as needed
            logging.info(f"\nProcessing Page {i + 1}")
            html = driver.page_source
            data = find_info(search_query, html)

            # Save to Excel after each page
            if data:
                save_to_excel(data)

            success = click_next(driver)
            if not success:
                break
        driver.quit()
        return data
    except Exception as e:
        logging.error(f"Error in scrape_google_places: {e}")
        return []
