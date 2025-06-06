import datetime
import logging
import sqlite3
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def coletar_produtos(setor_param, driver):
    """
    Collects product data from a specified sector on deliveryfort.com.br
    across multiple pages.

    Args:
        setor_param (str): The sector parameter to use in the URL (e.g., 'supermercado').
        driver: The Selenium WebDriver instance.

    Returns:
        list: A list of tuples, where each tuple contains (product_name, cleaned_price, setor_param).
    """
    all_products_data = []

    # Configure logging if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Define potential price element selectors in order of preference
    PRICE_SELECTORS = [
        (By.CLASS_NAME, 'shelf-item__best-price'),
        (By.CLASS_NAME, 'shelf-item__list-price'),
        (By.CSS_SELECTOR, '.shelf-item__buy-info .shelf-item__price span strong'),
        (By.CSS_SELECTOR, '.shelf-item__info strong'),
        (By.XPATH, './/*[contains(@class, "price")]//strong'),
        (By.XPATH, './/strong[contains(text(), "R$")]'),
        (By.CSS_SELECTOR, 'span[class*="price"]'),
        (By.CSS_SELECTOR, 'div[class*="price"]'),
        (By.TAG_NAME, 'strong')
    ]

    for page_num in range(1, 60):  # Changed to iterate through pages 1 to 10
        current_url = f'https://www.deliveryfort.com.br/{setor_param}?page={page_num}'
        logging.info(f"Navigating to page {page_num} for sector '{setor_param}': {current_url}")

        try:
            driver.get(current_url)
            time.sleep(2)  # Initial wait for page load

            # Scroll down to ensure all products are loaded.
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)  # Wait for new content to load
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            logging.debug(f"Finished scrolling page {page_num}. All dynamic content should be loaded.")

            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'shelf-item'))
            )
            logging.debug(f"Page {page_num} loaded successfully with product containers.")

            product_containers = driver.find_elements(By.CLASS_NAME, 'shelf-item')
            logging.info(
                f"Found {len(product_containers)} products on page {page_num} after scrolling for sector '{setor_param}'.")

            if not product_containers:
                logging.warning(
                    f"No product containers found on page {page_num} even after scrolling for sector '{setor_param}'. Moving to next page.")
                continue

            for i, container in enumerate(product_containers):
                product_name = "Unknown Product"  # Default value
                raw_price = None
                cleaned_price = None

                try:
                    title_element = container.find_element(By.CLASS_NAME, 'shelf-item__img-link')
                    product_name = title_element.get_attribute('title')
                except NoSuchElementException:
                    try:
                        name_element = container.find_element(By.CLASS_NAME, 'shelf-item__title')
                        product_name = name_element.get_attribute('innerText')
                    except NoSuchElementException:
                        logging.error(f"Product name could not be found for item {i + 1} on page {page_num}.")
                    except StaleElementReferenceException:
                        logging.warning(f"Stale element for product name on item {i + 1} on page {page_num}. Skipping.")
                        continue  # Skip this product if name element is stale
                except StaleElementReferenceException:
                    logging.warning(f"Stale element for product name on item {i + 1} on page {page_num}. Skipping.")
                    continue  # Skip this product if name element is stale
                except Exception as e:
                    logging.error(f"Unexpected error getting product name for item {i + 1} on page {page_num}: {e}")

                for selector_type, selector_value in PRICE_SELECTORS:
                    try:
                        price_element = container.find_element(selector_type, selector_value)
                        raw_price = price_element.get_attribute('innerText')
                        logging.debug(f"Raw price found for '{product_name}': {raw_price}")
                        break
                    except NoSuchElementException:
                        pass  # Try next selector
                    except StaleElementReferenceException:
                        logging.warning(
                            f"Stale element for price on item {i + 1} for '{product_name}' on page {page_num}. Skipping price.")
                        raw_price = None
                        break  # Break from price selector loop if stale
                    except Exception as e:
                        logging.error(
                            f"Unexpected error with price selector ({selector_type}, '{selector_value}') for '{product_name}': {e}")
                        raw_price = None
                        break  # Break if an unexpected error occurs during price finding

                # --- Price Cleaning and Conversion (moved outside the selector loop) ---
                if raw_price:
                    try:
                        cleaned_price = float(
                            raw_price.replace('R$', '').replace('.', '').replace(',', '.').strip()
                        )
                    except ValueError:
                        logging.warning(
                            f"Failed to convert price '{raw_price}' to float for product '{product_name}' on page {page_num}.")
                        cleaned_price = None
                else:
                    logging.warning(f"No price extracted for '{product_name}' on page {page_num}.")

                all_products_data.append((product_name, cleaned_price, setor_param))
                logging.debug(f"Collected: Name='{product_name}', Price={cleaned_price}, Sector='{setor_param}'")

            logging.info(
                f"Finished processing products on page {page_num} for sector '{setor_param}'. Total products collected so far: {len(all_products_data)}")

        except Exception as e:
            logging.critical(
                f"An unhandled error occurred while scraping page {page_num} for sector '{setor_param}': {e}",
                exc_info=True)
            break

    logging.info(f"Finished collecting products for sector '{setor_param}'. Total products: {len(all_products_data)}")
    return all_products_data


# --- Database Function ---
def salvar_dados_no_banco(produtos, db_name='fort.db', table_name='products'):
    """
    Saves product data to an SQLite database, including the current date.
    If a product with the same name and collection date exists, its price is updated.
    Otherwise, a new product record is inserted.

    Args:
        produtos (list): A list of tuples, where each tuple contains
                         (product_name, cleaned_price, setor_param).
        db_name (str): The name of the SQLite database file.
        table_name (str): The name of the table to store products.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        today_date = datetime.date.today().strftime('%Y-%m-%d')
        logging.info(f"Data de coleta para esta sessão: {today_date}")

        # Create the table if it does not exist.
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL,
                sector TEXT NOT NULL,
                date TEXT NOT NULL,
                UNIQUE(name, date) -- Ensures unique products by name and date for UPSERT
            );
        """)
        logging.info(f"Tabela '{table_name}' verificada/criada.")

        if produtos:
            inserted_count = 0
            updated_count = 0

            for product_name, cleaned_price, setor_param in produtos:
                # Attempt to update the existing record based on name, sector, AND today's date
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET price = ?
                    WHERE name = ? AND sector = ? AND date = ?;
                """, (cleaned_price, product_name, setor_param, today_date))

                if cursor.rowcount == 0:
                    # If no row was updated, the product for today's date does not exist, so insert it
                    cursor.execute(f"""
                        INSERT INTO {table_name} (name, price, sector, date)
                        VALUES (?, ?, ?, ?);
                    """, (product_name, cleaned_price, setor_param, today_date))
                    inserted_count += 1
                else:
                    updated_count += 1

            conn.commit()
            logging.info(
                f"Processamento de produtos concluído. {inserted_count} inseridos, {updated_count} atualizados.")
        else:
            logging.warning("Nenhum produto para inserir ou atualizar no banco de dados.")

        logging.info(f"Mostrando os primeiros 10 registros da tabela '{table_name}':")
        cursor.execute(f"SELECT id, name, price, sector, date FROM {table_name} LIMIT 10;")
        for row in cursor.fetchall():
            print(row)

    except sqlite3.Error as e:
        logging.error(f"Erro no banco SQLite: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logging.info("Conexão com o banco de dados encerrada.")


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
    # Removed duplicate 'hortifruti' and made it a set to ensure uniqueness if needed
    setores = list(set(['mercearia', 'bebidas', 'carnes-aves-e-peixes', 'hortifruti', 'higiene-e-beleza', 'limpeza',
                        'casa-e-lazer']))

    for setor in setores:
        try:
            produtos = coletar_produtos(setor, driver)
            salvar_dados_no_banco(produtos)
        except Exception as e:
            logging.critical(f"Erro crítico durante o processamento do setor '{setor}': {e}", exc_info=True)

    driver.quit()
    logging.info("Navegador encerrado.")
