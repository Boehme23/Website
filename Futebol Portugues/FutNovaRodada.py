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
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import logging

# --- Execução principal ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    ligas = [
        'francesa',
        'portuguesa',
        'inglesa',
        'alema',
        'espanhola',
        'neerlandesa'
    ]

    # Configurações do navegador
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Descomente se não quiser ver o browser a abrir
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = None

    try:
        driver = webdriver.Chrome(options=chrome_options)

        for liga in ligas:
            print(f"\n--- A processar liga: {liga} ---")
            url = f'https://www.zerozero.pt/competicao/liga-{liga}'

            try:
                # Chama a sua função de coleta
                lista_dados = coletar(driver, url)

                if lista_dados:
                    df_final = pd.DataFrame(lista_dados, columns=['Home', 'Away'])

                    # Salva o arquivo
                    nome_arquivo = f'Futebol {liga.capitalize()} Proximos Jogos.csv'
                    df_final.to_csv(nome_arquivo, index=False, header=True)

                    print(f"Sucesso! {len(df_final)} jogos extraídos.")
                    print(f"Salvo em: '{nome_arquivo}'")
                else:
                    print(f"Aviso: A função 'coletar' não retornou dados para a liga {liga}.")

            except Exception as e:
                logging.error(f"Erro ao processar a liga {liga}: {e}")
                # O 'continue' garante que se uma liga falhar, passa para a próxima
                continue

    except Exception as e:
        logging.error(f"Erro crítico no WebDriver: {e}")

    finally:
        if driver:
            driver.quit()
            logging.info("Navegador encerrado.")