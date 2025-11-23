import pandas as pd
import logging
import time
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def coletar(driver):
    """
    Collects data from multiple Transfermarkt pages, merges them on 'Clube',
    and returns a single combined DataFrame.
    """
    infolist = [
        'serien',
        'fairnesstabelle',
        'punktenachrueckstand',
        'punktenachfuehrung',
        'torverteilungart',
        'torschuetzenverteilung',
        'startseite',
        'chancenverwertung'
    ]

    # List to store DataFrames from each page
    collected_dfs = []

    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    for info in infolist:
        current_url = f'https://www.transfermarkt.pt/liga-nos/{info}/wettbewerb/PO1'
        logging.info(f"Navigating to {current_url}")
        driver.get(current_url)

        headers = []
        all_rows_data = []

        # --- Data Extraction Logic ---
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "items"))
            )
            logging.info("Table content appears to be loaded.")

            # --- 1. Extract Headers ---
            header_elements = driver.find_elements(By.XPATH, '//*[@id="yw1"]/table/thead/tr/th')
            for el in header_elements:
                div = el.find_elements(By.TAG_NAME, "div")
                if div and div[0].get_attribute("title"):
                    header_text = div[0].get_attribute("title").strip()
                else:
                    header_text = el.text.strip() or el.get_attribute("textContent").strip()

                if header_text:
                    headers.append(header_text)

            print(f"[{info}] Extracted columns:", headers)

            # --- 2. Extract Row Data ---
            table_rows = driver.find_elements(By.XPATH, "//tr[contains(@class, 'odd') or contains(@class, 'even')]")
            if len(table_rows) < 2:
                table_rows = driver.find_elements(By.XPATH, '//*[@id="yw1"]/table/tbody/tr')

            for i, row in enumerate(table_rows[:]):
                cells = row.find_elements(By.TAG_NAME, "td")
                row_data = []

                for cell in cells:
                    cell_text = ""
                    links = cell.find_elements(By.TAG_NAME, "a")

                    if links:
                        if len(links) > 1:
                            cell_text = links[1].text.strip()
                        else:
                            cell_text = links[0].text.strip()

                    if not cell_text:
                        cell_text = cell.text.strip()
                    if not cell_text:
                        cell_text = cell.get_attribute("textContent").strip()

                    row_data.append(cell_text)
                all_rows_data.append(row_data)

            # --- 3. Create DataFrame and Store---
            if all_rows_data:

                # 1. Determine the maximum observed width across all rows
                max_row_width = max(len(row) for row in all_rows_data)

                final_headers_list = headers

                # 2. Pad headers to match the max width if necessary
                if len(headers) < max_row_width:
                    missing_count = max_row_width - len(headers)
                    # append placeholder headers (since the missing column is usually the last position column)
                    final_headers_list =headers + [f'Hidden_Col_{i + 1}' for i in range(missing_count)]

                processed_rows = []
                # 3. Ensure all rows match the final header length (max_row_width)
                for row in all_rows_data:
                    # Pad shorter rows with empty strings
                    if len(row) < max_row_width:
                        processed_rows.append(row + [''] * (max_row_width - len(row)))
                    elif len(row) > max_row_width:
                        processed_rows.append(row[:max_row_width])
                    else:
                        processed_rows.append(row)

                # Create the DataFrame using the aligned headers and processed rows
                temp_df = pd.DataFrame(processed_rows, columns=final_headers_list)

                # Clean the 'Clube' column if present
                if 'Clube' in temp_df.columns:
                    temp_df['Clube'] = (
                        temp_df['Clube']
                        .str.replace(r'\d+.*$', '', regex=True)
                        .str.strip()
                    )

                # Define columns to drop, including original unwanted ones and temporary placeholders
                if 'name' in temp_df.columns:
                    # 1. Drop the existing 'Clube' column, if it exists
                    if 'Clube' in temp_df.columns:
                        temp_df = temp_df.drop('Clube', axis=1)

                        # 2. Rename the 'name' column to 'Clube'
                        temp_df = temp_df.rename(columns={'name': 'Clube'})
                cols_to_drop = ['wappen', '#'] + [h for h in final_headers_list if h.startswith('Hidden_Col')]
                temp_df = temp_df.drop(columns=cols_to_drop, errors='ignore')

                collected_dfs.append(temp_df)
                print(f"Successfully collected {len(temp_df)} rows for '{info}'.")

            time.sleep(3)

        except TimeoutException:
            logging.error(f"Timeout waiting for elements on page: {current_url}")
        except NoSuchElementException:
            logging.error(f"Required element not found on page: {current_url}")
        except StaleElementReferenceException:
            logging.error(f"Stale element encountered on page: {current_url}")
        except Exception as e:
            # Re-raise the error with detailed context for the problematic page
            logging.error(f"An unexpected error occurred while processing {current_url}: {e}")
            if all_rows_data:
                logging.error(
                    f"Rows collected (count): {len(all_rows_data)}. Header length: {len(headers)}. Max row length: {max(len(row) for row in all_rows_data)}")
            else:
                logging.error(f"No rows collected for this page.")
            # Continue the loop to try the next page if the error is non-fatal

    # --- 4. Combine all DataFrames using LEFT MERGE on 'Clube' ---
    if collected_dfs:
        # Start the final dataset with the first DataFrame collected
        final_dataset = collected_dfs[0]

        # Iterate over the remaining DataFrames and merge them sequentially
        for i in range(1, len(collected_dfs)):
            new_df = collected_dfs[i]

            # Use left merge to keep only rows with the right teams (there are pages with more extracted data than only the team)
            final_dataset = pd.merge(
                left=final_dataset,
                right=new_df,
                on='Clube',
                how='left',
                suffixes=('_x', f'_{i + 1}')
            )
            logging.info(f"Merged DataFrame {i + 1} on 'Clube'. Current shape: {final_dataset.shape}")

        if not final_dataset.empty:
            # --- SAVE DATAFRAME TO CSV FILE ---
            output_filename = 'Futebol Portugues.csv'

            final_dataset.to_csv(
                output_filename,
                index=False,
                encoding='utf-8'
            )
            print(f"\n✅ Data successfully saved to {output_filename}")
            print(f"Total rows collected: {len(final_dataset)}")
            return final_dataset

    logging.warning("No data collected.")
    return pd.DataFrame()


# --- Execução principal ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--enable-network-service-sync")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-extensions")

    try:
        driver = webdriver.Chrome(options=chrome_options)

        final_data = coletar(driver)

        driver.quit()
        logging.info("Navegador encerrado.")

        if not final_data.empty:
            print("\n--- Scrape Complete ---")
            print("You can inspect the saved CSV file 'Futebol Portugues.csv'.")

    except Exception as e:
        logging.error(f"Failed to initialize or run WebDriver: {e}")