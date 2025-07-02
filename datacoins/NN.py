import datetime
import os
import warnings

import numpy as np
import pandas as pd
import tensorflow as tf  # Only import tensorflow, not tensorflow.keras
from sklearn.preprocessing import MinMaxScaler

# Suppress specific FutureWarnings from pandas
warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")

# --- Set Random Seeds for Reproducibility ---
tf.random.set_seed(42)
np.random.seed(42)

# --- Configuration ---
INPUT_EXCEL_FILE = 'binance_all_usdt_daily_data.xlsx'
OUTPUT_PREDICTIONS_SUMMARY_FILE = 'binance_usdt_daily_predictions_nn_tf_summary.xlsx'  # New output file name
DATA_DIR = '.'  # Directory where your Excel files are located

# --- Machine Learning Configuration ---
N_LAG_DAYS = 5  # Number of previous days' 'Close' prices to use as features
NN_HIDDEN_LAYER_SIZE_1 = 64
NN_HIDDEN_LAYER_SIZE_2 = 32
NN_EPOCHS = 50
NN_BATCH_SIZE = 32
NN_LEARNING_RATE = 0.001


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
    if df.empty or len(df) <= n_lag_days + 1:
        return pd.DataFrame(), pd.Series(), pd.DataFrame(), None

    df = df.sort_index()

    for i in range(1, n_lag_days + 1):
        df[f'Close_Lag_{i}'] = df['Close'].shift(i)

    features = ['Open', 'High', 'Low', 'Volume', 'Number of trades'] + \
               [f'Close_Lag_{i}' for i in range(1, n_lag_days + 1)]

    df['Next_Day_Close'] = df['Close'].shift(-1)

    df_cleaned = df.dropna(subset=features + ['Next_Day_Close'])

    X = df_cleaned[features]
    y = df_cleaned['Next_Day_Close']

    df_temp = df.copy()
    for i in range(1, n_lag_days + 1):
        df_temp[f'Close_Lag_{i}'] = df_temp['Close'].shift(i)

    if not df_temp.dropna(subset=features).empty:
        latest_features = df_temp.dropna(subset=features).iloc[-1:][features]
    else:
        latest_features = pd.DataFrame()

    last_known_close = df['Close'].iloc[-1]

    return X, y, latest_features, last_known_close


# --- Manual Neural Network Implementation ---
class SimpleNeuralNetwork:
    def __init__(self, input_dim, hidden_size_1, hidden_size_2):
        # Initialize weights and biases as TensorFlow Variables
        # He initialization for ReLU activation
        self.W1 = tf.Variable(tf.random.normal([input_dim, hidden_size_1], stddev=tf.sqrt(2.0 / input_dim)), name='W1')
        self.b1 = tf.Variable(tf.zeros([hidden_size_1]), name='b1')

        self.W2 = tf.Variable(tf.random.normal([hidden_size_1, hidden_size_2], stddev=tf.sqrt(2.0 / hidden_size_1)),
                              name='W2')
        self.b2 = tf.Variable(tf.zeros([hidden_size_2]), name='b2')

        self.W_out = tf.Variable(tf.random.normal([hidden_size_2, 1], stddev=tf.sqrt(2.0 / hidden_size_2)),
                                 name='W_out')
        self.b_out = tf.Variable(tf.zeros([1]), name='b_out')

        self.trainable_variables = [self.W1, self.b1, self.W2, self.b2, self.W_out, self.b_out]

    def __call__(self, x):
        # Forward pass
        layer_1 = tf.nn.relu(tf.matmul(x, self.W1) + self.b1)
        layer_2 = tf.nn.relu(tf.matmul(layer_1, self.W2) + self.b2)
        output = tf.matmul(layer_2, self.W_out) + self.b_out  # Linear activation for regression
        return output

    def mse_loss(self, y_true, y_pred):
        return tf.reduce_mean(tf.square(y_true - y_pred))


def train_and_predict_neural_network_manual(X, y, latest_features):
    """
    Trains a Neural Network (manually implemented with TensorFlow) and makes a prediction.
    """
    if X.empty or y.empty or latest_features.empty:
        return None

    # --- Data Scaling ---
    x_scaler = MinMaxScaler()
    y_scaler = MinMaxScaler()

    X_scaled = x_scaler.fit_transform(X)
    y_scaled = y_scaler.fit_transform(y.values.reshape(-1, 1))

    latest_features_scaled = x_scaler.transform(latest_features)

    # --- Model Initialization ---
    input_dim = X_scaled.shape[1]
    model = SimpleNeuralNetwork(input_dim, NN_HIDDEN_LAYER_SIZE_1, NN_HIDDEN_LAYER_SIZE_2)
    optimizer = tf.optimizers.Adam(learning_rate=NN_LEARNING_RATE)

    # --- Training Loop ---
    # Convert data to TensorFlow tensors
    X_tensor = tf.convert_to_tensor(X_scaled, dtype=tf.float32)
    y_tensor = tf.convert_to_tensor(y_scaled, dtype=tf.float32)

    # Dataset for batching
    dataset = tf.data.Dataset.from_tensor_slices((X_tensor, y_tensor)).shuffle(buffer_size=len(X_scaled)).batch(
        NN_BATCH_SIZE)

    for epoch in range(NN_EPOCHS):
        # epoch_loss_avg = tf.keras.metrics.Mean() # Can use Keras metrics even without Keras models
        for x_batch, y_batch in dataset:
            with tf.GradientTape() as tape:
                y_pred_batch = model(x_batch)
                loss = model.mse_loss(y_batch, y_pred_batch)

            grads = tape.gradient(loss, model.trainable_variables)
            optimizer.apply_gradients(zip(grads, model.trainable_variables))
        # if epoch % 10 == 0:
        # print(f"  Epoch {epoch+1}/{NN_EPOCHS}, Loss: {loss.numpy():.6f}")

    # --- Make Prediction ---
    # Convert latest_features_scaled to tensor for prediction
    latest_features_tensor = tf.convert_to_tensor(latest_features_scaled, dtype=tf.float32)
    predicted_scaled = model(latest_features_tensor).numpy()
    predicted_value = y_scaler.inverse_transform(predicted_scaled)[0][0]

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

    print(f"\n--- Starting prediction for {len(all_coins_data)} USDT pairs using Manual Neural Network ---")

    for i, (sheet_name, df_coin) in enumerate(all_coins_data.items()):
        symbol = sheet_name
        print(f"\n[{i + 1}/{len(all_coins_data)}] Processing {symbol} for prediction...")

        if df_coin.empty:
            skipped_coins.append(f"{symbol} (empty DataFrame)")
            continue

        # Convert index to timezone-naive if it's timezone-aware (as it's read from Excel)
        if df_coin.index.tz is not None:
            df_coin.index = df_coin.index.tz_localize(None)

        X, y, latest_features, last_known_close = create_features_and_target(df_coin, N_LAG_DAYS)

        if not X.empty and not y.empty and not latest_features.empty:
            predicted_price = train_and_predict_neural_network_manual(X, y, latest_features)

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

        time.sleep(0.01)

    print("\n--- Prediction Summary ---")
    print(f"Successfully predicted for {len(predictions_results)} coins.")
    if skipped_coins:
        print(f"Skipped predictions for {len(skipped_coins)} coins: {', '.join(skipped_coins)}")

    predictions_df = pd.DataFrame(predictions_results)

    if not predictions_df.empty:
        predictions_df.sort_values(by='Predicted % Change', ascending=False, inplace=True)
        predictions_df['Last Known Close Price'] = predictions_df['Last Known Close Price'].round(4)
        predictions_df['Predicted Next Day Close'] = predictions_df['Predicted Next Day Close'].round(4)
        predictions_df['Predicted % Change'] = predictions_df['Predicted % Change'].round(2)

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
