from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
import numpy as np
import sqlite3
import requests
import logging
import time

def coletar(driver):
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        infolist = [
            'fairnesstabelle',
            'serien',
            'punktenachrueckstand',
            'punktenachfuehrung',
            'torverteilungart',
            'torschuetzenverteilung',
            'chancenverwertung'
        ]
        for info in infolist:
            current_url = f'https://www.transfermarkt.pt/liga-nos/'+info+'/wettbewerb/PO1'
            logging.info(f"Navigating to {current_url}")
            driver.get(current_url)
            # --- Find column names ---
            try:
                # Wait for table headers to be present
                # Wait for headers to appear
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//table[contains(@class,'items')]//th"))
                )

                # Get all potential header elements (either <a> or <div> inside <a>)
                header_elements = driver.find_elements(By.XPATH, "//table[contains(@class,'items')]//th//a")
                print(header_elements)
                print(header_elements[1].text.strip())
                column_names = []
                for el in header_elements:
                    # Try to read from <div title=""> first (if present)
                    div = el.find_elements(By.TAG_NAME, "div")
                    if div and div[0].get_attribute("title"):
                        header_text = div[0].get_attribute("title").strip()
                    else:
                        # Otherwise, fallback to <a> text or textContent
                        header_text = el.text.strip() or el.get_attribute("textContent").strip()

                    if header_text:
                        column_names.append(header_text)

                print("Extracted columns:", column_names)
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error while extracting column names: {e}")


# --- Execução principal ---
if __name__ == '__main__':
    # Configure root logger level if you want to see DEBUG messages from functions
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome without a GUI
    chrome_options.add_argument("--no-sandbox")  # Essential for environments like PythonAnywhere
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcomes limited resource issues
    chrome_options.add_argument("--disable-gpu")  # Important for some server setups
    chrome_options.add_argument("--window-size=1920,1080")  # Set a consistent window size
    chrome_options.add_argument("--enable-network-service-sync")  # Ensures network service is properly enabled
    chrome_options.add_argument("--disable-setuid-sandbox")  # Helps if --no-sandbox isn't enough
    chrome_options.add_argument("--disable-extensions")  # Disable extensions which could interfere
    driver = webdriver.Chrome(chrome_options)
    coletar(driver)
    driver.quit()
    logging.info("Navegador encerrado.")