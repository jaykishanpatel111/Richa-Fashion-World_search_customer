from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import pandas as pd
import os
import logging


# Set up logging for both file and console
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('saree_data_scraper.log')
file_formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logging.info("Script started.")


def open_browser(link):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disk-cache-size=0")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(link)

    logging.info("Now, wait for full page to load...")
    time.sleep(5)  # Adjust based on network speed

    return driver

def click_on_search_result(driver):
    try:
        wait = WebDriverWait(driver, 10)
        search_result = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="APjFqb"]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", search_result)
        search_result.click()
        logging.info("Clicked on the first search result.")
        return driver
    except Exception as e:
        logging.error("Failed to click on search result:", e)
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
        logging.error("Failed to type search query:", e)
        return driver

def find_info_old(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for span in soup.find_all("span", class_="OSrXXb"):
            name = span.get_text(strip=True)
            divs = []

            next_node = span.parent
            count = 0
            while next_node and count < 5:
                next_node = next_node.find_next_sibling()
                if next_node and next_node.name == "div":
                    divs.append(next_node.get_text(strip=True))
                    count += 1

            website = None
            container = span.find_parent("div")
            if container:
                link_tag = container.find_next("a", class_="yYlJEf")
                if link_tag:
                    website_div = link_tag.find("div", class_="BSaJxc")
                    if link_tag.has_attr("href") and website_div and "Website" in website_div.get_text():
                        website = link_tag["href"]
                    else:
                        website = None

            results.append({
                "name": name,
                "info": "\n".join(divs),
                "website": website
            })

        return results

    except Exception as e:
        logging.error(f"Error occurred during parsing: {e}")
        return []

def find_info_uk(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Loop through each result card
        for container in soup.select("a.rllt__link"):
            try:
                name = container.select_one("div.dbg0pd span.OSrXXb")
                name_text = name.get_text(strip=True) if name else None

                # Get all sibling divs after the name (inside rllt__details)
                details_div = container.select_one("div.rllt__details")
                if not details_div:
                    continue

                divs = details_div.find_all("div", recursive=False)
                address = None
                contact_number = None

                for div in divs:
                    text = div.get_text(strip=True)
                    if "United Kingdom" in text:
                        address = text
                    elif "+44" in text:
                        # This line may also contain status and open hours — extract number only
                        parts = text.split('·')
                        for part in parts:
                            if "+44" in part:
                                contact_number = part.strip()

                results.append({
                    "name": name_text,
                    "address": address,
                    "contact_number": contact_number
                })
            except Exception as inner_e:
                logging.warning(f"Failed to parse one block: {inner_e}")
                continue

        return results

    except Exception as e:
        logging.error(f"Error occurred during parsing: {e}")
        return []

import re

def find_info(search, html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for container in soup.select("a.rllt__link"):
            try:
                name_elem = container.select_one("div.dbg0pd span.OSrXXb")
                name = name_elem.get_text(strip=True) if name_elem else None

                # Get detail blocks inside 'rllt__details'
                details_div = container.select_one("div.rllt__details")
                if not details_div:
                    continue

                address = None
                contact_number = None

                info = []
                for div in details_div.find_all("div", recursive=False):
                    text = div.get_text(strip=True)
                    # logging.info(f"Processing text: {text}")
                    info.append(text)

                    # Detect phone numbers using pattern or "+" sign
                    if re.search(r'\+[\d\s\-()]+', text):
                        match = re.search(r'\+[\d\s\-()]+', text)
                        if match:
                            contact_number = match.group(0)

                    # Address heuristic: usually contains a comma and not "Closed", "Opens", etc.
                    elif ',' in text and not any(x in text.lower() for x in ['closed', 'opens', 'am', 'pm', 'fee']):
                        address = text

                results.append({
                    "search": search,
                    "name": name,
                    "address": address,
                    "contact_number": contact_number,
                    "info": "\n".join(info)
                })

            except Exception as inner_e:
                logging.warning(f"Error parsing card: {inner_e}")
                continue

        return results

    except Exception as e:
        logging.error(f"Error in find_info: {e}")
        return []


def click_next(driver):
    try:
        wait = WebDriverWait(driver, 10)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Next' or text()='التالي']/parent::a")))
        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
        next_button.click()
        logging.info("Clicked next button. Waiting for page to load...")
        time.sleep(5)
        return True
    except Exception as e:
        logging.error("Next button not found or not clickable:", e)
        return False


def save_to_excel(data, filename="saller_info.xlsx"):
    df_new = pd.DataFrame(data)
    if os.path.exists(filename):
        df_existing = pd.read_excel(filename)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_excel(filename, index=False)
    logging.info(f"Saved {len(data)} records to {filename}.")


if __name__ == "__main__":
    # link = "https://www.google.com/search?sa=X&sca_esv=2b90c4446a66ec78&hl=en&tbm=lcl&q=saree+shop+in+uk&rflfq=1&num=10&ved=2ahUKEwiE1MLHr8iOAxUsb_UHHVuuBrQQjGp6BAgcEAE&biw=1536&bih=695&dpr=1.25#rlfi=hd:;si:;mv:[[54.844693199999995,77.0449773],[21.2270519,-6.6803532]];tbs:lrf:!1m4!1u3!2m2!3m1!1e1!1m4!1u2!2m2!2m1!1e1!2m1!1e2!2m1!1e3!3sIAE,lf:1,lf_ui:10"
    link = "https://www.google.com/search?q=dress+shop+in+california&sca_esv=2b90c4446a66ec78&hl=en&biw=1536&bih=695&tbm=lcl&ei=j4N7aJyAG-qzvr0P5J2OqQM&ved=0ahUKEwjcg87h6siOAxXqma8BHeSOIzUQ4dUDCAo&uact=5&oq=dress+shop+in+california&gs_lp=Eg1nd3Mtd2l6LWxvY2FsIhhkcmVzcyBzaG9wIGluIGNhbGlmb3JuaWEyBhAAGBYYHjIGEAAYFhgeMgYQABgWGB4yBhAAGBYYHjIGEAAYFhgeMgYQABgWGB4yBhAAGBYYHjIGEAAYFhgeMgYQABgWGB4yBhAAGBYYHkj5OVDaBliJM3ABeACQAQCYAcABoAHBF6oBBDAuMTm4AQPIAQD4AQGYAhOgAvEWwgIFECEYoAHCAgQQIRgVwgIFECEYnwXCAgsQABiABBiGAxiKBcICCBAAGIAEGKIEwgIFEAAY7wXCAgUQABiABMICCxAAGIAEGJECGIoFmAMAiAYBkgcEMS4xOKAHoo0BsgcEMC4xOLgH6RbCBwQyLTE5yAda&sclient=gws-wiz-local#rlfi=hd:;si:;mv:[[38.465075899999995,-116.79096260000001],[32.27355,-122.25069130000001]];tbs:lrf:!1m4!1u3!2m2!3m1!1e1!1m4!1u2!2m2!2m1!1e1!2m1!1e2!2m1!1e3!3sIAE,lf:1,lf_ui:10"

    category_type = ["Saree shop", "Indian cloth wears", "Lehenga shop", "Shalwar suit shop", "Indian Ethnic Wears", "Indian Wears Dress", "Indian shop for Western Wears"]

    countries = ["UK", "USA", "AUSTRALIA", "NEW ZEALAND", "France", "Germany", "Sri Lanka", "Nepal", "Mauritius", "Fiji Island", "Reunion Island", "Singapore", "Malaysia", "South Africa", "UAE", "Canada", "Oman", "Bahrain", "Qatar", "Kuwait", "Switzerland"]    
    
    # search = 'dress shop in california'
    search = 'saree shop in uk'

    driver = open_browser(link)
    driver = click_on_search_result(driver)
    logging.info("Starting to scrape data...")
    time.sleep(5)  # Wait for the page to load after clicking
    driver = type_search_query(driver, search)
    time.sleep(5)  # Wait for the search results to load

    for i in range(2):  # Adjust the range as needed
        logging.info(f"\nProcessing Page {i + 1}")
        html = driver.page_source
        data = find_info(search, html)

        # Save to Excel after each page
        if data:
            save_to_excel(data)

        success = click_next(driver)
        if not success:
            break

    driver.quit()
    logging.info("\nScraping complete.")
