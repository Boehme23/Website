from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import logging
import time
import re
import pandas as pd

# Configuration
ligas = [
     ('ligue-1', 'FR1'),
     ('liga-nos', 'PO1'),
     ('eredivisie', 'NL1'),
     ('premier-league', 'GB1'),
     ('laliga', 'ES1'),
    ('bundesliga', 'L1')
]


def coletar_resultados_clean(driver, liga):
    url = f'https://www.transfermarkt.pt/{liga[0]}/gesamtspielplan/wettbewerb/{liga[1]}/saison_id/2025'
    logging.info(f"Processing: {liga[0]} | URL: {url}")
    driver.get(url)
    time.sleep(3)

    boxes = driver.find_elements(By.CSS_SELECTOR, "div.box")
    dados_limpos = []

    # Helper function defined once outside the loop
    def clean_team_final(text):
        # 1. Remove Date: dd/mm/yy
        text = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', text)
        # 2. Remove Days (sex, sáb, etc) - looks for word boundaries \b
        text = re.sub(r'\b(sex|sáb|dom|seg|ter|qua|qui)\b', '', text, flags=re.IGNORECASE)
        # 3. Remove standalone Time or leftover colon patterns (like 14:30)
        text = re.sub(r'\d{1,2}:\d{2}', '', text)
        # 4. Remove Ranks: (18.) or 1.
        text = re.sub(r'\(?\d+\.\)?', '', text)
        # 5. Clean whitespace
        return " ".join(text.split()).strip()

    for box in boxes:
        try:
            header_el = box.find_element(By.CSS_SELECTOR, ".content-box-headline")
            round_raw = header_el.get_attribute("innerText")
            round_num = re.sub(r'\D', '', round_raw)

            if not round_num: continue

            rows = box.find_elements(By.XPATH, ".//table/tbody/tr")
            for row in rows:
                raw_text = row.get_attribute("innerText").replace('\xa0', ' ')
                raw_text = " ".join(raw_text.split())

                # Find all time-like patterns (15:30, 2:1, etc.)
                matches = re.findall(r'(\d+:\d+)', raw_text)

                if matches:
                    # The Score is always the LAST match in the row
                    score = matches[-1]

                    # Split from the RIGHT based on the score to isolate Away Team
                    # This prevents splitting on the kick-off time if it exists
                    parts = raw_text.rsplit(score, 1)

                    home_team = clean_team_final(parts[0])
                    away_team = clean_team_final(parts[1])

                    if home_team and away_team:
                        dados_limpos.append({
                            'Round': round_num,
                            'Home': home_team,
                            'Result': score,
                            'Away': away_team
                        })
                        print(f"Added Round {round_num}: {home_team} {score} {away_team}")

        except Exception as e:
            continue

    if dados_limpos:
        df = pd.DataFrame(dados_limpos)
        filename = f"Schedule_{liga[0]}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info(f"Saved {len(df)} matches to {filename}")
    else:
        logging.warning(f"No data found for {liga[0]}")

# --- Main Execution ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--headless") # Uncomment to run invisible
    chrome_options.add_argument("window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        for liga in ligas:
            coletar_resultados_clean(driver, liga)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        driver.quit()
        logging.info("Browser closed.")