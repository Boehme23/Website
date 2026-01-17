from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import logging
import time
import re  # Importante para limpar o texto
import pandas as pd  # Importante para criar as colunas

ligas = [
    ('ligue-1', 'FR1','19'),
    ('liga-nos', 'PO1','19'),
    ('eredivisie', 'NL1','20'),
    ('premier-league', 'GB1','23'),
    ('laliga', 'ES1','21'),
    ('bundesliga', 'L1','18')
]

import logging
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By



def coletar_resultados_clean(driver, liga):
    url = f'https://www.transfermarkt.pt/{liga[0]}/spieltag/wettbewerb/{liga[1]}/plus/?saison_id=2025&spieltag={liga[2]}'

    logging.info(f"Acessando: {url}")
    driver.get(url)
    time.sleep(2)

    # --- NOVA PARTE: Capturar a Rodada (Round) ---
    try:
        # Tenta pegar o texto do cabeçalho da rodada (ex: "24. Jornada")
        round_element = driver.find_element(By.CSS_SELECTOR, ".content-box-headline")
        round_text = round_element.get_attribute("innerText")
        # Extrai apenas os números (ex: "24. Jornada" -> "24")
        round_number = re.findall(r'\d+', round_text)[0]
    except Exception:
        logging.warning("Não foi possível identificar a rodada automaticamente.")
        round_number = "0"

    logging.info(f"Iniciando extração da Rodada {round_number}...")

    elements = driver.find_elements(By.CSS_SELECTOR, ".table-grosse-schrift")
    dados_limpos = []

    if not elements:
        logging.warning("Nenhum resultado encontrado.")
    else:
        for el in elements:
            raw_text = el.get_attribute('outerText')

            if ':' in raw_text:
                text_no_rank = re.sub(r'\(\d+\.\)', '', raw_text)

                if '-:-' in text_no_rank:
                    splitter = '-:-'
                else:
                    splitter = ':'

                if splitter in text_no_rank:
                    parts = text_no_rank.split(splitter)
                    if len(parts) >= 2:
                        home_team = parts[0].strip()
                        away_team = parts[1].strip()

                        # Limpeza de caracteres residuais
                        home_team = re.sub(r'^[\d\.\s]+', '', home_team)
                        away_team = re.sub(r'\s*\d+[\.\s]*°.*$', '', away_team)

                        dados_limpos.append({
                            'Round': liga[2],
                            'Home': home_team.strip(),
                            'Away': away_team.strip()
                        })

    df = pd.DataFrame(dados_limpos)

    # Limpeza final das strings das equipes
    df['Home'] = df['Home'].str.replace(r'[^a-zA-ZÀ-ÿ\s]', '', regex=True).str.replace(r'\s+', ' ',
                                                                                       regex=True).str.strip()
    df['Away'] = df['Away'].str.replace(r'[^a-zA-ZÀ-ÿ\s]', '', regex=True).str.replace(r'\s+', ' ',
                                                                                       regex=True).str.strip()

    output_filename = f'Proximos Jogos da {liga[0]}.csv'
    df.to_csv(output_filename, index=False, encoding='utf-8')

    print(f"Total rows collected for Round {round_number}: {len(df)}")
    return df


# ... (restante do código de execução principal)
# --- Execução principal ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--headless") # Opcional: rodar sem abrir janela
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    for liga in ligas:
        try:
            df_resultados = coletar_resultados_clean(driver, liga)
        except Exception as e:
            logging.error(f"Erro durante a execução: {e}")
    driver.quit()
    logging.info("Navegador encerrado.")