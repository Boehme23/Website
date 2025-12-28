from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import logging
import time
import re  # Importante para limpar o texto
import pandas as pd  # Importante para criar as colunas

ligas = [
    ('ligue-1', 'FR1'),
    ('liga-nos', 'PO1'),
    ('eredivisie', 'NL1'),
    ('premier-league', 'GB1'),
    ('laliga', 'ES1'),
    ('bundesliga', 'L1')
]


def coletar_resultados_clean(driver, liga):
    url = f'https://www.transfermarkt.pt/{liga[0]}/spieltag/wettbewerb/{liga[1]}/saison_id/2025'

    logging.info(f"Acessando: {url}")
    driver.get(url)
    time.sleep(2)

    logging.info("Iniciando extração...")

    elements = driver.find_elements(By.CSS_SELECTOR, ".table-grosse-schrift")

    dados_limpos = []

    if not elements:
        logging.warning("Nenhum resultado encontrado.")
    else:
        print(f"Encontrados {len(elements)} resultados. Processando...")

        for el in elements:
            raw_text = el.get_attribute('outerText')

            # Verifica se a linha tem o separador de jogo "-:-" ou resultado "2:1"
            # O transfermarkt usa ":", então vamos dividir por isso
            if ':' in raw_text:
                # 1. Remover os rankings ex: (8.) ou (12.) usando Regex
                # O padrão r'\(\d+\.\)' busca parenteses, digitos, ponto e fecha parenteses
                text_no_rank = re.sub(r'\(\d+\.\)', '', raw_text)

                # 2. Dividir em Casa e Fora baseado no separador central
                # Se o jogo não aconteceu é "-:-", se aconteceu pode ser "2:1"
                if '-:-' in text_no_rank:
                    splitter = '-:-'
                else:
                    # Caso pegue jogos passados, tenta dividir pelo resultado (arriscado, mas funcional)
                    # O ideal para jogos futuros é focar no -:-
                    splitter = ':'

                if splitter in text_no_rank:
                    parts = text_no_rank.split(splitter)
                    if len(parts) >= 2:
                        home_team = parts[0].strip()
                        away_team = parts[1].strip()
                        home_team = re.sub(r'^[\d\.\s]+', '', home_team)
                        away_team = re.sub(r'\s*\d+[\.\s]*°.*$', '', away_team)
                        dados_limpos.append({
                            'Home': home_team.strip(),
                            'Away': away_team.strip()
                        })

    # Cria o DataFrame
    df = pd.DataFrame(dados_limpos)
    df['Home'] = df['Home'].str.replace(r'[^a-zA-ZÀ-ÿ\s]', '', regex=True)
    df['Away'] = df['Away'].str.replace(r'[^a-zA-ZÀ-ÿ\s]', '', regex=True)

    # 2. Clean up extra whitespace (e.g., double spaces or tabs left behind)
    df['Home'] = df['Home'].str.replace(r'\s+', ' ', regex=True).str.strip()
    df['Away'] = df['Away'].str.replace(r'\s+', ' ', regex=True).str.strip()

    output_filename = f'Proximos Jogos da {liga[0]}.csv'

    df.to_csv(
        output_filename,
        index=False,
        encoding='utf-8'
    )
    print(f"\n✅ Data successfully saved to {output_filename}")
    print(f"Total rows collected: {len(df)}")
    return df

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