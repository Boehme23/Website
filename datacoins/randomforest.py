import datetime
import os
import time
import warnings

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# Suppress specific FutureWarnings from pandas
warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")

# --- Configuration ---
INPUT_EXCEL_FILE = 'binance_all_usdt_daily_data.xlsx'
OUTPUT_PREDICTIONS_SUMMARY_FILE = 'binance_usdt_daily_predictions_summary.xlsx'  # New output file name
DATA_DIR = '.'  # Directory where your Excel files are located

# --- Machine Learning Configuration ---
N_LAG_DAYS = 5  # Number of previous days' 'Close' prices to use as features


def clean_sheet_name(symbol):
    """Ensures sheet name is valid for Excel."""
    sheet_name = symbol.replace('/', '_').replace('\\', '_').replace('?', '').replace('*', '').replace('[', '').replace(
        ']', '').replace(':', '')
    if len(sheet_name) > 31:  # Excel sheet name limit
        sheet_name = sheet_name[:31]
    return sheet_name


def load_all_coin_data(excel_path):
    """Loads all sheets from the Excel file."""
    try:
        # sheet_name=None loads all sheets into a dictionary of DataFrames
        all_dfs = pd.read_excel(excel_path, sheet_name=None, index_col='Open time', parse_dates=True)
        print(f"Loaded {len(all_dfs)} sheets from '{excel_path}'.")
        return all_dfs
    except FileNotFoundError:
        print(f"Error: Input Excel file '{excel_path}' not found. Please ensure it exists.")
        return {}
    except Exception as e:
        print(f"Error loading all data from Excel: {e}")
        return {}


def create_features_and_target(df, n_lag_days):
    """
    Creates lagged features and the target variable for prediction.
    Features: 'Open', 'High', 'Low', 'Volume', 'Number of trades', and N lagged 'Close' prices.
    Target: Next day's 'Close' price.
    Returns: X (features), y (target), latest_features (features for the last known day),
             last_known_close (actual close for the last known day).
    """
    if df.empty or len(df) <= n_lag_days + 1:  # Need enough data for lags + target + 1 for current features
        return pd.DataFrame(), pd.Series(), pd.DataFrame(), None

    # Ensure data is sorted by date
    df = df.sort_index()

    # Create lagged 'Close' price features
    for i in range(1, n_lag_days + 1):
        df[f'Close_Lag_{i}'] = df['Close'].shift(i)

    # Define features (X) and target (y)
    features = ['Open', 'High', 'Low', 'Volume', 'Number of trades'] + \
               [f'Close_Lag_{i}' for i in range(1, n_lag_days + 1)]

    # Target is the next day's 'Close' price
    df['Next_Day_Close'] = df['Close'].shift(-1)

    # Drop rows with NaN values created by lagging and shifting (first N rows and last row for target)
    df_cleaned = df.dropna(subset=features + ['Next_Day_Close'])

    X = df_cleaned[features]
    y = df_cleaned['Next_Day_Close']

    # Get the features for the very last day in your original (un-shifted) data
    # This row will be used to predict the *next* day's close
    df_temp = df.copy()  # Use the original df for this part
    for i in range(1, n_lag_days + 1):
        df_temp[f'Close_Lag_{i}'] = df_temp['Close'].shift(i)

    # The last row that has all the required features is what we use for today's prediction input
    # Ensure there's at least one row after feature creation that is not NaN
    if not df_temp.dropna(subset=features).empty:
        latest_features = df_temp.dropna(subset=features).iloc[-1:][features]
    else:
        latest_features = pd.DataFrame()  # No valid latest features if all are NaN

    # Get the last known actual close price from the original (unsorted) df, or df if sorted already
    # Ensure to get the last value before creating 'Next_Day_Close' or dropping NaNs
    last_known_close = df['Close'].iloc[-1]

    return X, y, latest_features, last_known_close


def train_and_predict(X, y, latest_features):
    """
    Trains a Random Forest Regressor and makes a prediction.
    latest_features: Features for the absolute last known day to predict the *next* value.
    """
    if X.empty or y.empty or latest_features.empty:
        return None

    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X, y)

    predicted_value = model.predict(latest_features)[0]
    return predicted_value


# --- Main execution ---
if __name__ == "__main__":
    full_input_excel_path = os.path.join(DATA_DIR, INPUT_EXCEL_FILE)
    all_coins_data = load_all_coin_data(full_input_excel_path)

    if not all_coins_data:
        print("No data loaded from the input Excel file. Exiting prediction script.")
        exit()

    predictions_results = []
    skipped_coins = []

    print(f"\n--- Starting prediction for {len(all_coins_data)} USDT pairs ---")

    for i, (sheet_name, df_coin) in enumerate(all_coins_data.items()):
        symbol = sheet_name  # Assuming sheet_name is the symbol for simplicity
        print(f"\n[{i + 1}/{len(all_coins_data)}] Processing {symbol} for prediction...")

        # Convert index to timezone-naive if it's timezone-aware (as it's read from Excel)
        # This is crucial because create_features_and_target expects a clean dataframe
        if df_coin.index.tz is not None:
            df_coin.index = df_coin.index.tz_localize(None)

        # Create features and target
        X, y, latest_features, last_known_close = create_features_and_target(df_coin, N_LAG_DAYS)

        if not X.empty and not y.empty and not latest_features.empty:
            predicted_price = train_and_predict(X, y, latest_features)

            if predicted_price is not None:
                predicted_change = ((
                                            predicted_price - last_known_close) / last_known_close) * 100 if last_known_close != 0 else 0
                predictions_results.append({
                    'Symbol': symbol,
                    'Last Known Close Price': last_known_close,
                    'Predicted Next Day Close': predicted_price,
                    'Predicted % Change': predicted_change
                })
            else:
                skipped_coins.append(f"{symbol} (prediction failed)")
        else:
            skipped_coins.append(f"{symbol} (not enough data or features for prediction)")

        # Add a small delay for print statements in long runs (not API related here)
        time.sleep(0.01)

    print("\n--- Prediction Summary ---")
    print(f"Successfully predicted for {len(predictions_results)} coins.")
    if skipped_coins:
        print(f"Skipped predictions for {len(skipped_coins)} coins: {', '.join(skipped_coins)}")

    # --- Create a new DataFrame for results ---
    predictions_df = pd.DataFrame(predictions_results)

    # --- Order the results ---
    if not predictions_df.empty:
        predictions_df.sort_values(by='Predicted % Change', ascending=False, inplace=True)
        predictions_df['Last Known Close Price'] = predictions_df['Last Known Close Price'].round(4)
        predictions_df['Predicted Next Day Close'] = predictions_df['Predicted Next Day Close'].round(4)
        predictions_df['Predicted % Change'] = predictions_df['Predicted % Change'].round(2)

    # --- Save predictions to a new Excel file ---
    full_output_predictions_path = os.path.join(DATA_DIR, OUTPUT_PREDICTIONS_SUMMARY_FILE)
    if not predictions_df.empty:
        try:
            predictions_df.to_excel(full_output_predictions_path, index=False)
            print(f"\nAll predictions summary saved to '{full_output_predictions_path}' successfully!")
        except Exception as e:
            print(f"Error saving predictions summary to Excel: {e}")
    else:
        print("\nNo predictions were generated to save.")

    print(f"\n--- Prediction Script Finished ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
