import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from datetime import date

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

# ==========================================
# 2. LOAD DATA
# ==========================================
print("Loading data...")
try:
    df_stats = pd.read_csv(FILES['stats'])
    df_history = pd.read_csv(FILES['history'])
    df_upcoming = pd.read_csv(FILES['upcoming'])
except FileNotFoundError as e:
    print(f"Error: {e}")
    exit()

# ==========================================
# 2.5. CONVERT SCORES TO RESULTS
# ==========================================
def get_result_from_score(score_str):
    if pd.isna(score_str) or '-' not in str(score_str):
        return None
    try:
        parts = str(score_str).split('-')
        home, away = int(parts[0]), int(parts[1])
        if home > away: return 'H'
        elif away > home: return 'A'
        else: return 'D'
    except:
        return None

print("Converting scores...")
df_history['FTR'] = df_history[COLS['score_col']].apply(get_result_from_score)
df_history = df_history.dropna(subset=['FTR'])
target_col = 'FTR'

# ==========================================
# 3. MERGE TEAM STATS
# ==========================================
def merge_team_stats(matches_df, stats_df):
    merged = matches_df.merge(stats_df, left_on=COLS['home_team'], right_on=COLS['team_name'], how='left')
    merged = merged.rename(columns={c: f'Home_{c}' for c in stats_df.columns if c != COLS['team_name']})
    merged = merged.merge(stats_df, left_on=COLS['away_team'], right_on=COLS['team_name'], how='left', suffixes=('', '_Away'))
    merged = merged.rename(columns={c: f'Away_{c}' for c in stats_df.columns if c != COLS['team_name']})
    return merged

print("Merging team data...")
train_data = merge_team_stats(df_history, df_stats)
predict_data = merge_team_stats(df_upcoming, df_stats)

# ==========================================
# 4. FEATURE SELECTION
# ==========================================
exclude_cols = [COLS['home_team'], COLS['away_team'], COLS['score_col'], target_col,
                COLS['match_date'], COLS['team_name'], 'Home_' + COLS['team_name'], 'Away_' + COLS['team_name']]

features = [c for c in train_data.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(train_data[c])]

X = train_data[features].fillna(0)
y = train_data[target_col]
X_new = predict_data[features].fillna(0)

print(f"Features used: {len(features)} variables")

# ==========================================
# 5A. RANDOM FOREST MODEL
# ==========================================
print("\n--- Training Random Forest ---")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=23)

clf = RandomForestClassifier(n_estimators=500, random_state=23)
clf.fit(X_train, y_train)
print(f"Random Forest Accuracy: {accuracy_score(y_test, clf.predict(X_test)):.2f}")

# Retrain on full data and predict
clf.fit(X, y)
rf_predictions = clf.predict(X_new)

# ==========================================
# 5B. NEURAL NETWORK MODEL
# ==========================================
print("\n--- Training Neural Network ---")

# 1. Scale Data (Required for NN)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X_new_scaled = scaler.transform(X_new)

# Split for validation
X_train_nn, X_test_nn, y_train_nn, y_test_nn = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# 2. Build and Train the Model
nn_clf = MLPClassifier(hidden_layer_sizes=(64, 32), activation='relu', max_iter=500, random_state=42)
nn_clf.fit(X_train_nn, y_train_nn)

# 3. Evaluate
nn_acc = accuracy_score(y_test_nn, nn_clf.predict(X_test_nn))
print(f"Neural Network Accuracy: {nn_acc:.2f}")

# 4. Retrain on FULL data and Predict
nn_clf.fit(X_scaled, y)
nn_predictions = nn_clf.predict(X_new_scaled)

# ==========================================
# 6. COMBINE & SAVE RESULTS
# ==========================================
print("\nSaving results...")

# Save Random Forest Results
df_upcoming['RF_Prediction'] = rf_predictions
# Save Neural Network Results
df_upcoming['NN_Prediction'] = nn_predictions

# Helper to get team names
def get_winner_name(row, pred_col):
    res = row[pred_col]
    if res == 'H': return row[COLS['home_team']]
    elif res == 'A': return row[COLS['away_team']]
    else: return 'Draw'

df_upcoming['RF_Winner_Name'] = df_upcoming.apply(lambda row: get_winner_name(row, 'RF_Prediction'), axis=1)
df_upcoming['NN_Winner_Name'] = df_upcoming.apply(lambda row: get_winner_name(row, 'NN_Prediction'), axis=1)

# Check for agreement (Confidence Booster)
df_upcoming['Models_Agree'] = df_upcoming['RF_Prediction'] == df_upcoming['NN_Prediction']

# Select Columns for Final CSV
output_columns = [COLS['home_team'], COLS['away_team'],
                  'RF_Winner_Name', 'NN_Winner_Name', 'Models_Agree']

if COLS['match_date'] in df_upcoming.columns:
    output_columns.insert(0, COLS['match_date'])

final_results = df_upcoming[output_columns].copy()

output_filename = 'prediction_results_combined_'+date.today().strftime('%d-%m')+'.csv'
final_results.to_csv(output_filename, index=False)
print(f"Done! Predictions saved to {output_filename}")