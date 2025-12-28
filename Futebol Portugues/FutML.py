import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from datetime import date
import sys

# ==========================================
# 1. CONFIGURATION
# ==========================================
FILES = {
    'stats': 'Futebol Portugues.csv',
    'history': 'Futebol Portugues Jogos.csv',
    'upcoming': 'Futebol Portugues Proximos Jogos.csv'
}

COLS = {
    'team_name': 'Clube',
    'home_team': 'Home',
    'away_team': 'Away',
    'score_col': 'Score',
    'match_date': 'Round'
}

# Threshold for removing correlated features (0.90 = 90%)
CORRELATION_THRESHOLD = 0.80

# ==========================================
# 2. LOAD DATA
# ==========================================
print("Loading data...")
try:
    df_stats = pd.read_csv(FILES['stats'])
    df_history = pd.read_csv(FILES['history'])
    df_upcoming = pd.read_csv(FILES['upcoming'])

    # Clean column names (strip whitespace)
    df_stats.columns = df_stats.columns.str.strip()
    df_history.columns = df_history.columns.str.strip()
    df_upcoming.columns = df_upcoming.columns.str.strip()

except FileNotFoundError as e:
    print(f"Error: {e}")
    sys.exit()

# ==========================================
# 2.1. AUTO-DETECT NEXT ROUND
# ==========================================
print("Calculating next round...")
try:
    if COLS['match_date'] in df_history.columns:
        history_rounds = pd.to_numeric(df_history[COLS['match_date']], errors='coerce')
        max_round = history_rounds.max()

        if pd.isna(max_round):
            print("Warning: Could not find any valid round numbers. Defaulting to 1.")
            next_round = 1
        else:
            next_round = int(max_round) + 1

        print(f"-> Highest Round in History: {int(max_round)}")
        print(f"-> Predicting for Round: {next_round}")
        df_upcoming[COLS['match_date']] = next_round
    else:
        print(f"Warning: Column '{COLS['match_date']}' not found in history.")

except Exception as e:
    print(f"Error calculating next round: {e}")


# ==========================================
# 2.5. CONVERT SCORES TO RESULTS
# ==========================================
def get_result_from_score(score_str):
    if pd.isna(score_str) or '-' not in str(score_str):
        return None
    try:
        parts = str(score_str).split('-')
        home, away = int(parts[0]), int(parts[1])
        if home > away:
            return 'H'
        elif away > home:
            return 'A'
        else:
            return 'D'
    except:
        return None


print("Converting scores...")
if COLS['score_col'] in df_history.columns:
    df_history['FTR'] = df_history[COLS['score_col']].apply(get_result_from_score)
    df_history = df_history.dropna(subset=['FTR'])
    target_col = 'FTR'
else:
    print(f"Error: Score column '{COLS['score_col']}' not found.")
    sys.exit()


# ==========================================
# 3. MERGE TEAM STATS
# ==========================================
def merge_team_stats(matches_df, stats_df):
    if COLS['home_team'] not in matches_df.columns or COLS['away_team'] not in matches_df.columns:
        print("Error: Home/Away team columns missing.")
        return matches_df

    merged = matches_df.merge(stats_df, left_on=COLS['home_team'], right_on=COLS['team_name'], how='left')
    merged = merged.rename(columns={c: f'Home_{c}' for c in stats_df.columns if c != COLS['team_name']})

    merged = merged.merge(stats_df, left_on=COLS['away_team'], right_on=COLS['team_name'], how='left',
                          suffixes=('', '_Away'))
    merged = merged.rename(columns={c: f'Away_{c}' for c in stats_df.columns if c != COLS['team_name']})

    return merged


print("Merging team data...")
train_data = merge_team_stats(df_history, df_stats)
predict_data = merge_team_stats(df_upcoming, df_stats)

# ==========================================
# 4. FEATURE SELECTION & CORRELATION REMOVAL
# ==========================================
exclude_cols = [COLS['home_team'], COLS['away_team'], COLS['score_col'], target_col,
                COLS['match_date'], COLS['team_name'], 'Home_' + COLS['team_name'], 'Away_' + COLS['team_name']]

# Initial list of numeric features
raw_features = [c for c in train_data.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(train_data[c])]

print(f"Initial numeric features: {len(raw_features)}")

# --- 4.1. REMOVE HIGHLY CORRELATED FEATURES ---
print("\n--- Correlation Analysis ---")
# Calculate correlation matrix
corr_matrix = train_data[raw_features].corr().abs()

# Create a boolean mask for the upper triangle
upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

# Find features with correlation greater than threshold
to_drop = [column for column in upper_tri.columns if any(upper_tri[column] > CORRELATION_THRESHOLD)]

print(f"Detected {len(to_drop)} features with correlation > {CORRELATION_THRESHOLD}")
print(f"Dropping: {to_drop}")

# Define final feature set
features = [f for f in raw_features if f not in to_drop]

print(f"Final Features used: {len(features)} variables")

if len(features) == 0:
    print("Error: No features remaining after correlation filtering.")
    sys.exit()

# Prepare Data
X = train_data[features].fillna(0)
y = train_data[target_col]
X_new = predict_data[features].fillna(0)

# ==========================================
# 5A. RANDOM FOREST MODEL
# ==========================================
print("\n--- Training Random Forest ---")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=23)

clf = RandomForestClassifier(n_estimators=500, random_state=23)
clf.fit(X_train, y_train)
print(f"Random Forest Accuracy: {accuracy_score(y_test, clf.predict(X_test)):.2f}")

# Retrain on full data
clf.fit(X, y)
rf_predictions = clf.predict(X_new)

# ==========================================
# 5B. NEURAL NETWORK MODEL
# ==========================================
print("\n--- Training Neural Network ---")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X_new_scaled = scaler.transform(X_new)

X_train_nn, X_test_nn, y_train_nn, y_test_nn = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

nn_clf = MLPClassifier(hidden_layer_sizes=(64, 32), activation='relu', max_iter=500, random_state=42)
nn_clf.fit(X_train_nn, y_train_nn)

nn_acc = accuracy_score(y_test_nn, nn_clf.predict(X_test_nn))
print(f"Neural Network Accuracy: {nn_acc:.2f}")

nn_clf.fit(X_scaled, y)
nn_predictions = nn_clf.predict(X_new_scaled)

# ==========================================
# 6. COMBINE & SAVE RESULTS
# ==========================================
print("\nSaving results...")

df_upcoming['RF_Prediction'] = rf_predictions
df_upcoming['NN_Prediction'] = nn_predictions


def get_winner_name(row, pred_col):
    res = row[pred_col]
    if res == 'H':
        return row[COLS['home_team']]
    elif res == 'A':
        return row[COLS['away_team']]
    else:
        return 'Draw'


df_upcoming['RF_Winner_Name'] = df_upcoming.apply(lambda row: get_winner_name(row, 'RF_Prediction'), axis=1)
df_upcoming['NN_Winner_Name'] = df_upcoming.apply(lambda row: get_winner_name(row, 'NN_Prediction'), axis=1)
df_upcoming['Models_Agree'] = df_upcoming['RF_Prediction'] == df_upcoming['NN_Prediction']

output_columns = [COLS['home_team'], COLS['away_team'],
                  'RF_Winner_Name', 'NN_Winner_Name', 'Models_Agree']

if COLS['match_date'] in df_upcoming.columns:
    output_columns.insert(0, COLS['match_date'])

final_results = df_upcoming[output_columns].copy()

output_filename = 'prediction_results.csv'

if os.path.exists(output_filename):
    try:
        df_existing = pd.read_csv(output_filename)
        df_combined = pd.concat([df_existing, final_results], ignore_index=True)

        rows_before = len(df_combined)
        df_final_export = df_combined.drop_duplicates()
        rows_after = len(df_final_export)

        duplicates_removed = rows_before - rows_after

        if duplicates_removed > 0:
            print(f"Merged data and removed {duplicates_removed} duplicate row(s).")
        else:
            print("Merged data. No duplicates found.")

        df_final_export.to_csv(output_filename, index=False)
        print(f"Updated {output_filename} successfully.")

    except pd.errors.EmptyDataError:
        final_results.to_csv(output_filename, index=False)
        print(f"Existing file was empty. Saved new predictions to {output_filename}")
else:
    final_results.to_csv(output_filename, index=False)
    print(f"Created new file: {output_filename}")