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
dataset=pd.DataFrame()

def coletar(driver):
    infolist=[
        'fairnesstabelle',
        'serien',
        'punktenachrueckstand',
        'punktenachfuehrung',
        'torverteilungart',
        'torschuetzenverteilung',
        'chancenverwertung'
          ]
    for info in infolist:
        column_names = []
        # Configure logging if not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        current_url = f'https://www.transfermarkt.pt/liga-nos/'+info+'/wettbewerb/PO1'
        logging.info(f"Navigating to {current_url}")
        driver.get(current_url)
        # --- Data Extraction Logic ---
        try:
            # Wait up to 10 seconds for the main table (often identified by a class or ID)
            try:
                # Wait for the table to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "items"))
                )
                logging.info("Table content appears to be loaded.")
                header_elements = driver.find_elements(By.XPATH, '//*[@id="yw1"]/table/thead/tr/th')
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
                # Find all rows with odd/even class
                table_rows = driver.find_elements(By.XPATH, "//tr[contains(@class, 'odd') or contains(@class, 'even')]")
                if len(table_rows)<2:
                    table_rows = driver.find_elements(By.XPATH,'//*[@id="yw1"]/table/tbody/tr')
                for i, row in enumerate(table_rows[:-4]):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    row_data = []

                    for cell in cells:
                        # Default: text directly inside <td>
                        cell_text = cell.text.strip()

                        # Get all <a> elements inside the cell
                        links = cell.find_elements(By.TAG_NAME, "a")

                        # If there are links, prefer the second one’s title/text
                        if links:
                            if len(links) > 1:
                                cell_text = links[1].text.strip()
                            else:
                                cell_text = links[0].text.strip()

                        # As a final fallback, if text is still empty, use <td> text
                        if not cell_text:
                            cell_text = cell.get_attribute("textContent").strip()

                        row_data.append(cell_text)
                    column_names.append(row_data)
                print(column_names)
                time.sleep(3)
                if dataset is not None :
                    dataset= pd.DataFrame(column_names)
                else:
                    pd.join(dataset,column_names,'clubes')


            except Exception as e:
                logging.error(f"Error during data collection or wait: {e}")

        except Exception as e:
            logging.error(f"Error during data collection or wait: {e}")


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