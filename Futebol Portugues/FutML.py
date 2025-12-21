import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# ==========================================
# 1. CONFIGURATION
# ==========================================
FILES = {
    'stats': 'Futebol Portugues.csv',  # File with team characteristics
    'history': 'Futebol Portugues Jogos.csv',  # File with past results
    'upcoming': 'Futebol Portugues Proximos Jogos.csv'  # File with games to predict
}

COLS = {
    'team_name': 'Clube',  # Name of team in stats file
    'home_team': 'Home',  # Home team column in matches
    'away_team': 'Away',  # Away team column in matches
    'score_col': 'Score',  # The column with "2-1", "0-0", etc.
    'match_date': 'Round'  # Date/Round column
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
    print("Please make sure the CSV files are in the same folder.")
    exit()


# ==========================================
# 2.5. CONVERT SCORES TO RESULTS (THE FIX)
# ==========================================
def get_result_from_score(score_str):

    if pd.isna(score_str) or '-' not in str(score_str):
        return None

    try:
        # Split '2-1' into parts
        parts = str(score_str).split('-')
        home = int(parts[0])
        away = int(parts[1])

        if home > away:
            return 'H'  # Home Win
        elif away > home:
            return 'A'  # Away Win
        else:
            return 'D'  # Draw
    except:
        return None


print("Converting scores (e.g. '2-1') into results (H/D/A)...")
# Create a new column 'FTR' (Full Time Result) based on the Score
df_history['FTR'] = df_history[COLS['score_col']].apply(get_result_from_score)

# Remove games where the score was invalid or missing
df_history = df_history.dropna(subset=['FTR'])

# Update the target column to be this new 'FTR' column
target_col = 'FTR'


# ==========================================
# 3. DATA PREPROCESSING & MERGING
# ==========================================
def merge_team_stats(matches_df, stats_df):
    # Merge Home Team Stats
    merged = matches_df.merge(stats_df, left_on=COLS['home_team'], right_on=COLS['team_name'], how='left')
    merged = merged.rename(columns={c: f'Home_{c}' for c in stats_df.columns if c != COLS['team_name']})

    # Merge Away Team Stats
    merged = merged.merge(stats_df, left_on=COLS['away_team'], right_on=COLS['team_name'], how='left',
                          suffixes=('', '_Away'))
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

print(f"Features used: {features}")

X = train_data[features].fillna(0)
y = train_data[target_col]

# ==========================================
# 5. MODEL TRAINING
# ==========================================
print("Training Random Forest model...")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=23)

clf = RandomForestClassifier(n_estimators=500, random_state=23)
clf.fit(X_train, y_train)

predictions = clf.predict(X_test)
print(f"Model Accuracy on Test Set: {accuracy_score(y_test, predictions):.2f}")

# Retrain on full data
clf.fit(X, y)

# ==========================================
# 6. PREDICT UPCOMING MATCHES
# ==========================================
print("Predicting incoming matches...")

X_new = predict_data[features].fillna(0)
future_predictions = clf.predict(X_new)
future_probs = clf.predict_proba(X_new)

df_upcoming['Predicted_Result'] = future_predictions

# Map probabilities correctly based on class order
# classes_ usually comes out as ['A', 'D', 'H'] (Alphabetical)
classes = list(clf.classes_)
print(f"Class order detected: {classes}")

if 'H' in classes and 'D' in classes and 'A' in classes:
    h_index = classes.index('H')
    d_index = classes.index('D')
    a_index = classes.index('A')

    df_upcoming['Prob_Home_Win'] = future_probs[:, h_index]
    df_upcoming['Prob_Draw'] = future_probs[:, d_index]
    df_upcoming['Prob_Away_Win'] = future_probs[:, a_index]

# ==========================================
# 7. SAVE RESULTS
# ==========================================
print("Saving results...")

# Create a clean dataframe for the output
# We select the original team name columns + the new prediction columns
# CHECK: Make sure COLS['home_team'] matches your CSV header (e.g. 'Home')
output_columns = [COLS['home_team'], COLS['away_team'], 'Predicted_Result', 'Prob_Home_Win', 'Prob_Draw', 'Prob_Away_Win']

# If you also want the Date/Round, add it:
if COLS['match_date'] in df_upcoming.columns:
    output_columns.insert(0, COLS['match_date'])

# Create the final file
final_results = df_upcoming[output_columns].copy()

# OPTIONAL: Make the prediction easier to read
# Instead of 'H', 'A', 'D', let's print the actual Winning Team Name
def get_winner_name(row):
    pred = row['Predicted_Result']
    if pred == 'H':
        return row[COLS['home_team']]  # Return Home Team Name
    elif pred == 'A':
        return row[COLS['away_team']]  # Return Away Team Name
    else:
        return 'Draw'

final_results['Predicted_Winner'] = final_results.apply(get_winner_name, axis=1)

# Save to CSV
output_filename = 'prediction_results.csv'
final_results.to_csv(output_filename, index=False)
print(f"Done! Predictions saved to {output_filename}")