import datetime
import os
import time

import pandas as pd
from binance.client import Client

# --- Configuration ---
API_KEY = ''  # Replace with your Binance API Key if needed
API_SECRET = ''  # Replace with your Binance API Secret if needed
OUTPUT_EXCEL_FILE = 'binance_all_usdt_daily_data.xlsx'
DATA_DIR = '.'  # Or a specific directory like 'data/' where your excel file resides

client = Client(API_KEY, API_SECRET)


def get_all_spot_symbols():
    """Fetches all spot trading symbols from Binance."""
    try:
        exchange_info = client.get_exchange_info()
        symbols = [s['symbol'] for s in exchange_info['symbols'] if
                   s['status'] == 'TRADING' and s['isSpotTradingAllowed']]
        print(f"Found {len(symbols)} total trading symbols.")
        return symbols
    except Exception as e:
        print(f"Error fetching symbols: {e}. Check API key/secret or network connection.")
        return []


def get_klines_from_timestamp(symbol, start_timestamp_ms, end_timestamp_ms=None, max_retries=3, retry_delay=5):
    """
    Fetches kline data for a given symbol from a specific start timestamp.
    start_timestamp_ms: Unix timestamp in milliseconds for the start date.
    end_timestamp_ms: Unix timestamp in milliseconds for the end date (optional, defaults to now).
    """
    for attempt in range(max_retries):
        try:
            klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, start_timestamp_ms,
                                                  end_timestamp_ms)

            if not klines:
                end_dt_str = datetime.datetime.fromtimestamp(end_timestamp_ms / 1000,
                                                             tz=datetime.timezone.utc).strftime(
                    '%Y-%m-%d') if end_timestamp_ms else "now"
                print(
                    f"No new kline data found for {symbol} from {datetime.datetime.fromtimestamp(start_timestamp_ms / 1000, tz=datetime.timezone.utc).strftime('%Y-%m-%d')} to {end_dt_str}")
                return pd.DataFrame()

            df = pd.DataFrame(klines, columns=[
                'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
                'Close time', 'Quote asset volume', 'Number of trades',
                'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
            ])

            df['Open time'] = pd.to_datetime(df['Open time'], unit='ms', utc=True)
            df['Close time'] = pd.to_datetime(df['Close time'], unit='ms', utc=True)

            numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume',
                            'Quote asset volume', 'Number of trades',
                            'Taker buy base asset volume', 'Taker buy quote asset volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

            df = df.set_index('Open time')
            df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Number of trades']]

            df['%_Change'] = df['Close'].pct_change() * 100
            df['%_Change'] = df['%_Change'].round(2)

            print(f"Successfully fetched {len(df)} new daily candles for {symbol}")
            return df

        except Exception as e:
            print(f"Error fetching klines for {symbol} (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Max retries reached for {symbol}. Skipping.")
                return pd.DataFrame()


def main():
    print(f"--- Daily Update Script Started ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")

    all_symbols = get_all_spot_symbols()
    if not all_symbols:
        print("No symbols found. Exiting.")
        return

    usdt_symbols = [s for s in all_symbols if s.endswith('USDT')]
    if not usdt_symbols:
        print("No USDT pairs found. Exiting.")
        return

    # Use a subset for testing, comment out for all USDT pairs
    # usdt_symbols = usdt_symbols[:10]
    print(f"Processing {len(usdt_symbols)} USDT pairs for update...")

    full_excel_path = os.path.join(DATA_DIR, OUTPUT_EXCEL_FILE)
    existing_data_dfs = {}
    if os.path.exists(full_excel_path):
        print(f"Loading existing data from '{full_excel_path}'...")
        try:
            existing_data_dfs = pd.read_excel(full_excel_path, sheet_name=None, index_col='Open time', parse_dates=True)
            for sheet_name, df in existing_data_dfs.items():
                if not df.empty and df.index.tz is None:
                    existing_data_dfs[sheet_name].index = df.index.tz_localize('UTC')
                if existing_data_dfs[sheet_name].index.name is None:
                    existing_data_dfs[sheet_name].index.name = 'Open time'
            print("Existing data loaded.")
        except Exception as e:
            print(f"Error loading existing Excel file: {e}. Starting fresh.")
            existing_data_dfs = {}

    updated_coins_count = 0
    skipped_coins_count = 0
    all_coins_data_to_save = {}

    empty_df_template = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume', 'Number of trades', '%_Change'])
    empty_df_template.index.name = 'Open time'
    empty_df_template.index = pd.to_datetime(empty_df_template.index, utc=True)

    for i, symbol in enumerate(usdt_symbols):
        print(f"\n[{i + 1}/{len(usdt_symbols)}] Processing {symbol}...")

        sheet_name = symbol.replace('/', '_').replace('\\', '_').replace('?', '').replace('*', '').replace('[',
                                                                                                           '').replace(
            ']', '').replace(':', '')
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:31]

        existing_df = existing_data_dfs.get(sheet_name, empty_df_template.copy())

        if not existing_df.empty:
            existing_df.index = pd.to_datetime(existing_df.index, utc=True)
            existing_df = existing_df.loc[~existing_df.index.duplicated(keep='last')]
            existing_df = existing_df.sort_index()

        last_recorded_dt_utc = existing_df.index.max() if not existing_df.empty else None

        if last_recorded_dt_utc:
            start_fetch_dt_utc = last_recorded_dt_utc + datetime.timedelta(days=1)
            print(f"Last recorded date for {symbol}: {last_recorded_dt_utc.strftime('%Y-%m-%d')}")
        else:
            print(f"No valid existing data for {symbol}. Fetching from default start date.")
            start_fetch_dt_utc = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

        today_utc = datetime.datetime.now(datetime.UTC).replace(hour=0, minute=0, second=0, microsecond=0,
                                                                tzinfo=datetime.timezone.utc)

        if start_fetch_dt_utc > today_utc:
            print(
                f"Data for {symbol} is already up to date. Skipping fetch (last data {last_recorded_dt_utc.strftime('%Y-%m-%d')} is beyond today {today_utc.strftime('%Y-%m-%d')}).")
            skipped_coins_count += 1
            all_coins_data_to_save[sheet_name] = existing_df
            continue

        start_timestamp_ms = int(start_fetch_dt_utc.timestamp() * 1000)

        new_df = get_klines_from_timestamp(symbol, start_timestamp_ms, end_timestamp_ms=None)

        list_to_concat = []
        if not existing_df.empty:
            list_to_concat.append(existing_df)
        if not new_df.empty:
            new_df.index = pd.to_datetime(new_df.index, utc=True)
            list_to_concat.append(new_df)

        if list_to_concat:
            combined_df = pd.concat(list_to_concat)
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            combined_df = combined_df.sort_index()
            combined_df = combined_df.reindex(columns=empty_df_template.columns)

            all_coins_data_to_save[sheet_name] = combined_df
            updated_coins_count += 1
        else:
            all_coins_data_to_save[sheet_name] = empty_df_template.copy()
            skipped_coins_count += 1

        time.sleep(0.1)

    print("\n--- Update Summary ---")
    print(f"Successfully updated data for {updated_coins_count} symbols.")
    print(f"Skipped {skipped_coins_count} symbols (no new data or error).")

    # --- Save all updated data back to the single XLSX file ---
    print(f"\nSaving all updated data to '{full_excel_path}'...")
    try:
        with pd.ExcelWriter(full_excel_path, engine='xlsxwriter') as writer:
            for sheet_name, df_to_save in all_coins_data_to_save.items():
                if not df_to_save.empty:
                    # --- NEW FIX: Remove timezone information from index before saving ---
                    if df_to_save.index.tz is not None:
                        df_to_save.index = df_to_save.index.tz_localize(None)  # Make timezone-naive (UTC)

                    df_to_save.to_excel(writer, sheet_name=sheet_name, index=True)
                    print(f"Saved sheet '{sheet_name}' with {len(df_to_save)} records.")
                else:
                    # Ensure empty_df_template's index is also timezone-naive before saving
                    temp_empty_df_for_save = empty_df_template.copy()
                    if temp_empty_df_for_save.index.tz is not None:
                        temp_empty_df_for_save.index = temp_empty_df_for_save.index.tz_localize(None)

                    temp_empty_df_for_save.to_excel(writer, sheet_name=sheet_name, index=True)
                    print(f"Saved empty sheet '{sheet_name}' (no data).")
        print(f"\nAll updated data saved to '{full_excel_path}' successfully!")
    except Exception as e:
        print(f"Error saving updated data to Excel: {e}")

    print(f"--- Daily Update Script Finished ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")


if __name__ == "__main__":
    main()
