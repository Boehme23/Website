from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.options import Options
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

def coletar_resultados_clean(driver):
    url = 'https://www.flashscore.pt/futebol/portugal/liga-portugal-betclic/resultados/'
    driver.get(url)
    try:
        cookie_btn = WebDriverWait(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
        cookie_btn.click()
        logging.info("Cookies accepted.")
        time.sleep(1)
    except:
        logging.info("Cookie banner not found or already closed.")

        # --- 2. Click "Show more games" until it's gone ---
    logging.info("Loading more games...")
    while True:
        try:
            more_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='wcl-buttonLink']"))
            )

            # Use JavaScript click (more reliable than standard .click() for this specific button)
            driver.execute_script("arguments[0].click();", more_button)

            logging.info("Clicked 'Show more matches'. Waiting for load...")
            time.sleep(2)  # Give the site time to load the new rows

        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            # If the button is not found or not clickable, we have reached the end
            logging.info("No more matches to load.")
            break
        except Exception as e:
            logging.warning(f"Unexpected error clicking button: {e}")
            break

    # --- 3. Scrape Data ---
    logging.info("Starting extraction...")
    elements = driver.find_elements(By.CSS_SELECTOR, ".event__round, .event__match")

    data = []
    current_round = "Unknown"

    for el in elements:
        class_name = el.get_attribute("class")

        # 1. If it's a Round Header, update state
        if "event__round" in class_name:
            current_round = el.text.strip().split()[-1]

        # 2. If it's a Match, extract data
        elif "event__match" in class_name:
            try:
                # Use relative selectors (dot at the start) to find elements INSIDE this match
                home = el.find_element(By.CSS_SELECTOR, ".event__homeParticipant").text.split('\n')[0]
                away = el.find_element(By.CSS_SELECTOR, ".event__awayParticipant").text.split('\n')[0]

                # Check if scores exist (sometimes games are postponed)
                try:
                    s_home = el.find_element(By.CSS_SELECTOR, ".event__score--home").text
                    s_away = el.find_element(By.CSS_SELECTOR, ".event__score--away").text
                    score = f"{s_home}-{s_away}"
                except:
                    score = "Postponed/Pending"

                data.append({
                    "Round": current_round,
                    "Home": home,
                    "Away": away,
                    "Score": score
                })
            except Exception as e:
                continue

    if not pd.DataFrame(data).empty:
        # --- SAVE DATAFRAME TO CSV FILE ---
        output_filename = 'Futebol Portugues Jogos.csv'

        print(f"Total rows collected: {len(pd.DataFrame(data))}")
        mapper={
            "AFS":"Avs - Futebol SAD",
            "Casa Pia AC":"Casa Pia AC",
            "Nacional":"CD Nacional",
            "Santa Clara":"CD Santa Clara",
            "Tondela":"CD Tondela",
            "Estrela da Amadora":"CF Estrela Amadora",
            "Alverca":"FC Alverca",
            "Arouca":"FC Arouca",
            "Famalicão":"FC Famalicão",
            "FC Porto": "FC Porto",
            "Estoril": "GD Estoril Praia",
            "Gil Vincente": "Gil Vincente FC",
            "Moreirense": "Moreirense FC",
            "Rio Ave": "Rio Ave FC",
            "Braga": "SC Braga",
            "Benfica": "SL Benfica",
            "Sporting CP": "Sporting CP",
            "Vitória SC": "Vitória SC"
        }
        dados=pd.DataFrame(data)
        dados['Home'] = dados['Home'].replace(mapper)
        dados['Away'] = dados['Away'].replace(mapper)
        print('dados modificados')

        dados.to_csv(
            output_filename,
            index=False,
            encoding='utf-8'
        )
        print(f"\n✅ Data successfully saved to {output_filename}")
        return dados

# --- Execução principal ---
if __name__ == '__main__':
    # Configure root logger level if you want to see DEBUG messages from functions
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    chrome_options = Options() # Run Chrome without a GUI
    chrome_options.add_argument("--no-sandbox")  # Essential for environments like PythonAnywhere
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcomes limited resource issues
    chrome_options.add_argument("--disable-gpu")  # Important for some server setups
    chrome_options.add_argument("--window-size=1920,1080")  # Set a consistent window size
    chrome_options.add_argument("--enable-network-service-sync")  # Ensures network service is properly enabled
    chrome_options.add_argument("--disable-setuid-sandbox")  # Helps if --no-sandbox isn't enough
    chrome_options.add_argument("--disable-extensions")  # Disable extensions which could interfere
    driver = webdriver.Chrome(chrome_options)
    coletar_resultados_clean(driver)
    driver.quit()
    logging.info("Navegador encerrado.")