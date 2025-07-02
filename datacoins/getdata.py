import datetime
import time

import pandas as pd
from binance.client import Client

# --- IMPORTANT ---
# You generally don't need API_KEY and API_SECRET for public market data,
# but the python-binance client might still expect them to be provided.
# If you plan to make authenticated requests, replace with your actual API Key and Secret.
# For public market data, you can leave them as empty strings if the client allows.
API_KEY = ''  # Replace with your Binance API Key if needed
API_SECRET = ''  # Replace with your Binance API Secret if needed

client = Client(API_KEY, API_SECRET)


def get_all_spot_symbols():
    """Fetches all spot trading symbols from Binance."""
    try:
        exchange_info = client.get_exchange_info()
        # Filter for TRADING status and Spot Trading allowed
        symbols = [s['symbol'] for s in exchange_info['symbols'] if
                   s['status'] == 'TRADING' and s['isSpotTradingAllowed']]
        print(f"Found {len(symbols)} total trading symbols.")
        return symbols
    except Exception as e:
        print(f"Error fetching symbols: {e}. Check API key/secret or network connection.")
        return []


def get_daily_klines(symbol, start_timestamp_ms, end_timestamp_ms=None, max_retries=3, retry_delay=5):
    """
    Fetches daily kline data for a given symbol with retry logic.
    start_timestamp_ms: Unix timestamp in milliseconds for the start date.
    end_timestamp_ms: Unix timestamp in milliseconds for the end date (optional, defaults to now).
    """
    for attempt in range(max_retries):
        try:
            # Pass timestamps directly to avoid string parsing ambiguity
            klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, start_timestamp_ms,
                                                  end_timestamp_ms)

            if not klines:
                print(
                    f"No kline data found for {symbol} from {datetime.datetime.fromtimestamp(start_timestamp_ms / 1000).strftime('%Y-%m-%d')} to {datetime.datetime.now().strftime('%Y-%m-%d') if not end_timestamp_ms else datetime.datetime.fromtimestamp(end_timestamp_ms / 1000).strftime('%Y-%m-%d')}")
                return pd.DataFrame()

            df = pd.DataFrame(klines, columns=[
                'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
                'Close time', 'Quote asset volume', 'Number of trades',
                'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
            ])

            df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
            df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
            numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume',
                            'Quote asset volume', 'Number of trades',
                            'Taker buy base asset volume', 'Taker buy quote asset volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

            df = df.set_index('Open time')
            df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Number of trades']]

            print(f"Successfully fetched {len(df)} daily candles for {symbol}")
            return df

        except Exception as e:
            print(f"Error fetching klines for {symbol} (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Max retries reached for {symbol}. Skipping.")
                return pd.DataFrame()


# --- Main execution ---
if __name__ == "__main__":
    all_symbols = get_all_spot_symbols()

    # Define the start date as a datetime object
    # This avoids ambiguous string parsing by python-binance
    start_dt = datetime.datetime(2024, 1, 1, 0, 0, 0)  # January 1, 2024, 00:00:00
    # To get a date like "90 days ago":
    # start_dt = datetime.datetime.now() - datetime.timedelta(days=90)

    # Convert datetime object to Unix timestamp in milliseconds
    start_timestamp_ms = int(start_dt.timestamp() * 1000)

    # Note: For end_str, if you want "until now", you can simply omit it or calculate
    # datetime.datetime.now() and convert to timestamp.
    # Binance API typically defaults to 'now' if end_str is not provided.
    end_timestamp_ms = None  # To fetch data until the current moment

    # Filter for USDT trading pairs
    usdt_symbols = [s for s in all_symbols if s.endswith('USDT')]
    print(f"Found {len(usdt_symbols)} USDT pairs.")

    # --- WARNING: Fetching ALL USDT pairs can take a very long time and hit rate limits ---
    # For demonstration, you might want to uncomment this line to limit the number of symbols:
    # usdt_symbols = usdt_symbols[:10] # Limit to first 10 USDT pairs for testing

    print(f"Attempting to fetch daily data for {len(usdt_symbols)} USDT pairs...")

    all_coins_daily_data = {}
    successful_fetches = 0
    skipped_fetches = 0

    for i, symbol in enumerate(usdt_symbols):
        print(f"\n[{i + 1}/{len(usdt_symbols)}] Fetching data for {symbol}...")
        # Pass the timestamp directly to the function
        df_coin = get_daily_klines(symbol, start_timestamp_ms, end_timestamp_ms)
        if not df_coin.empty:
            all_coins_daily_data[symbol] = df_coin
            successful_fetches += 1
        else:
            skipped_fetches += 1
        # Add a small delay to respect API rate limits.
        # This will be significant for many symbols.
        time.sleep(0.1)  # Increased frequency for more symbols, but monitor for 429s

    print("\n--- Summary of fetched data ---")
    print(f"Successfully fetched data for {successful_fetches} symbols.")
    print(f"Skipped data for {skipped_fetches} symbols.")

    # --- Save data to a single XLSX file with multiple sheets ---
    output_excel_file = 'binance_all_usdt_daily_data.xlsx'
    try:
        # Using xlsxwriter engine is recommended for writing multiple sheets
        with pd.ExcelWriter(output_excel_file, engine='xlsxwriter') as writer:
            for symbol, df in all_coins_daily_data.items():
                # Ensure sheet name is valid (max 31 chars, no invalid chars like '/', ':', '*', etc.)
                # and remove characters not allowed in sheet names
                sheet_name = symbol.replace('/', '_').replace('\\', '_').replace('?', '').replace('*', '').replace('[',
                                                                                                                   '').replace(
                    ']', '').replace(':', '')
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:31]  # Truncate if too long
                df.to_excel(writer, sheet_name=sheet_name)
                print(f"Saved {symbol} data to sheet '{sheet_name}'")
        print(f"\nAll fetched USDT daily data saved to '{output_excel_file}' successfully!")
    except Exception as e:
        print(f"Error saving data to Excel: {e}")
