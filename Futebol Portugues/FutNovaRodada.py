import pandas as pd
import logging
import time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def coletar(driver, url):
    """
    Navega até a página, extrai os dados da tabela de jogos e retorna uma lista de dicionários.
    """
    # A URL está correta para a Liga Portuguesa
    logging.info(f"Navigating to {url}")
    driver.get(url)

    # Lista para armazenar todos os dados extraídos
    games = []

    try:
        # Espera que a tabela principal de jogos (tbody) esteja presente
        tabela_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='fixture_games']/table/tbody"))
        )
        logging.info("Table content appears to be loaded.")

        # Encontra todas as linhas de jogos (tr) dentro da tabela
        linhas_jogos = tabela_element.find_element(By.XPATH, "//*[@id='fixture_games']/table/tbody")
        jogos= linhas_jogos.find_elements(By.CLASS_NAME, "text")
        i=0
        dupla=[]
        for linha in jogos:
            dados_jogos = linha.get_attribute('outerText')
            i=1+i
            dupla.append(dados_jogos)
            if i%2==0:
                games.append(dupla)
                dupla=[]

        logging.info(f"Successfully extracted {len(dados_jogos)} games.")
        return games

    except TimeoutException:
        logging.error(f"Timeout waiting for elements on page: {url}")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing {url}: {e}")
        return []


# --- Execução principal ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    url = 'https://www.zerozero.pt/competicao/liga-portuguesa'  # URL mais específica para a temporada

    # Configurações do navegador (headless)
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Removi algumas opções redundantes ou não essenciais para manter o código limpo

    driver = None
    try:
        # Inicializa o driver
        driver = webdriver.Chrome(options=chrome_options)

        # Coleta os dados (retorna uma lista de dicionários)
        lista_dados = coletar(driver, url)

        # Converte a lista de dicionários em um DataFrame do Pandas

        df_final = pd.DataFrame(lista_dados,columns=['Home', 'Away']
)
    except Exception as e:
        logging.error(f"Failed to initialize or run WebDriver: {e}")
        df_final = pd.DataFrame()

    finally:
        if driver:
            driver.quit()
            logging.info("Navegador encerrado.")

    # Processamento final dos dados
    if not df_final.empty:
        # Salva o DataFrame em CSV
        nome_arquivo = 'Futebol Portugues Proximos Jogos.csv'
        df_final.to_csv(nome_arquivo, index=False, header=True)

        print("\n--- Scrape Complete ---")
        print(f"Total de jogos extraídos: {len(df_final)}")
        print(f"Primeiras 5 linhas do DataFrame:\n{df_final.head()}")
        print(f"\nOs dados foram salvos no arquivo '{nome_arquivo}'.")
    else:
        print("\n--- Scrape Falhou ---")
        print("Não foi possível extrair dados válidos. Verifique os logs de erro.")