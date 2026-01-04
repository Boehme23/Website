import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
import sys

# ==========================================
# 1. CONFIGURATION
# ==========================================
FILES = {
    'stats': 'All_Leagues_Combined.csv',
    'history': 'All_Schedule_Combined.csv',
    'upcoming': 'All_Proximos_Jogos.csv'
}

COLS = {
    'team_name': 'Clube',
    'home_team': 'Home',
    'away_team': 'Away',
    'score_col': 'Result',
    'match_date': 'Round',
    'league': 'League'
}

CORRELATION_THRESHOLD = 0.80

# ==========================================
# 2. LOAD & CLEAN DATA
# ==========================================
print("Loading data...")
try:
    df_stats = pd.read_csv(FILES['stats'])
    df_history = pd.read_csv(FILES['history'])
    df_upcoming = pd.read_csv(FILES['upcoming'])

    for df in [df_stats, df_history, df_upcoming]:
        df.columns = df.columns.str.strip()
except FileNotFoundError as e:
    print(f"Error: {e}")
    sys.exit()

def clean_numeric_strings(val):
    if pd.isna(val) or not isinstance(val, str): return val
    val = val.replace('%', '').replace('€', '').replace(' ', '')
    multiplier = 1000 if 'milM' in val else 1
    val = val.replace('milM', '').replace('M', '').replace(',', '.')
    try:
        return float(val) * multiplier
    except:
        return np.nan

print("Cleaning stats data...")
cols_to_fix = ['Cartões amarelos', 'Pontos', 'Valor de mercado total', 'ø-Idade', 'ø-valor de mercado', 'Taxa']
for col in cols_to_fix:
    if col in df_stats.columns:
        df_stats[col] = df_stats[col].apply(clean_numeric_strings)

# ==========================================
# 2.2 PER-LEAGUE ROUND DETECTION
# ==========================================
print("Calculating next round per league...")
league_round_map = df_history.groupby(COLS['league'])[COLS['match_date']].max()

def assign_round(row):
    league = row[COLS['league']]
    return league_round_map.get(league, 0)

df_upcoming[COLS['match_date']] = df_upcoming.apply(assign_round, axis=1)

# ==========================================
# 2.3 CONVERT SCORES
# ==========================================
def get_result_from_score(score_str):
    if pd.isna(score_str): return None
    score_str = str(score_str).replace(':', '-')
    if '-' not in score_str: return None
    try:
        parts = score_str.split('-')
        h, a = int(parts[0]), int(parts[1])
        return 'H' if h > a else ('A' if a > h else 'D')
    except:
        return None

df_history['FTR'] = df_history[COLS['score_col']].apply(get_result_from_score)
df_history = df_history.dropna(subset=['FTR'])
target_col = 'FTR'

# ==========================================
# 3. MERGE TEAM STATS
# ==========================================
def merge_team_stats(matches_df, stats_df):
    for c in [COLS['home_team'], COLS['away_team']]: matches_df[c] = matches_df[c].str.strip()
    stats_df[COLS['team_name']] = stats_df[COLS['team_name']].str.strip()

    merged = matches_df.merge(stats_df, left_on=COLS['home_team'], right_on=COLS['team_name'], how='left')
    merged = merged.rename(
        columns={c: f'Home_{c}' for c in stats_df.columns if c not in [COLS['team_name'], COLS['league']]})

    merged = merged.merge(stats_df, left_on=COLS['away_team'], right_on=COLS['team_name'], how='left',
                          suffixes=('', '_Away'))
    merged = merged.rename(columns={c: f'Away_{c}' for c in stats_df.columns if
                                    c not in [COLS['team_name'], COLS['league']] and not c.startswith('Home_')})
    return merged

train_data = merge_team_stats(df_history, df_stats)
predict_data = merge_team_stats(df_upcoming, df_stats)

# ==========================================
# 4. FEATURE SELECTION
# ==========================================
exclude_cols = [COLS['home_team'], COLS['away_team'], COLS['score_col'], target_col,
                COLS['match_date'], COLS['team_name'], COLS['league'], 'League_Away']

raw_features = [c for c in train_data.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(train_data[c])]
train_data = train_data.dropna(subset=raw_features)

corr_matrix = train_data[raw_features].corr().abs()
upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
to_drop = [column for column in upper_tri.columns if any(upper_tri[column] > CORRELATION_THRESHOLD)]
features = [f for f in raw_features if f not in to_drop]

X, y = train_data[features], train_data[target_col]
X_new = predict_data[features].fillna(X.median())

# ==========================================
# 5. TRAINING & EVALUATION
# ==========================================
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

clf_test = RandomForestClassifier(n_estimators=500, random_state=23).fit(X_train, y_train)
rf_acc = accuracy_score(y_test, clf_test.predict(X_test))

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
nn_clf_test = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42).fit(X_train_scaled, y_train)
nn_acc = accuracy_score(y_test, nn_clf_test.predict(scaler.transform(X_test)))

print(f"\nRandom Forest Accuracy: {rf_acc:.2%}")
print(f"Neural Network Accuracy: {nn_acc:.2%}")

# ==========================================
# 5.1 FEATURE IMPORTANCE CHART
# ==========================================
def plot_feature_importance(model, feature_list):
    importances = model.feature_importances_
    feature_imp_df = pd.DataFrame({'Feature': feature_list, 'Importance': importances})
    feature_imp_df = feature_imp_df.sort_values(by='Importance', ascending=False).head(15)

    plt.figure(figsize=(10, 6))
    sns.barplot(x='Importance', y='Feature', data=feature_imp_df, palette='viridis')
    plt.title('Top 15 Most Important Features (Random Forest)')
    plt.tight_layout()

    # SAVE THE IMAGE
    filename = 'feature_importance.png'
    plt.savefig(filename)
    print(f"\nFeature importance chart saved as: {filename}")

    # Close the plot so it doesn't stay in memory or try to pop up
    plt.close()
# ==========================================
# 6. FINAL PREDICTIONS
# ==========================================
clf_final = RandomForestClassifier(n_estimators=500, random_state=23).fit(X, y)
scaler_final = StandardScaler()
X_scaled_full = scaler_final.fit_transform(X)
nn_clf_final = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42).fit(X_scaled_full, y)

X_new_scaled = scaler_final.transform(X_new)
rf_preds = clf_final.predict(X_new)
rf_probs = clf_final.predict_proba(X_new).max(axis=1)
nn_preds = nn_clf_final.predict(X_new_scaled)
nn_probs = nn_clf_final.predict_proba(X_new_scaled).max(axis=1)

# ==========================================
# 7. SAVE RESULTS
# ==========================================
def get_winner(pred, row):
    if pred == 'H': return row[COLS['home_team']]
    if pred == 'A': return row[COLS['away_team']]
    return 'Draw'

results_list = []
for i in range(len(df_upcoming)):
    row = df_upcoming.iloc[i]
    results_list.append({
        COLS['match_date']: row[COLS['match_date']],
        COLS['league']: row[COLS['league']],
        COLS['home_team']: row[COLS['home_team']],
        COLS['away_team']: row[COLS['away_team']],
        'RF_Winner': get_winner(rf_preds[i], row),
        'RF_Conf': f"{rf_probs[i]:.1%}",
        'NN_Winner': get_winner(nn_preds[i], row),
        'NN_Conf': f"{nn_probs[i]:.1%}",
        'Agree': rf_preds[i] == nn_preds[i]
    })

df_new_preds = pd.DataFrame(results_list)
if os.path.exists('prediction_results.csv'):
    df_combined = pd.concat([pd.read_csv('prediction_results.csv'), df_new_preds], ignore_index=True)
else:
    df_combined = df_new_preds

df_final = df_combined.drop_duplicates(subset=[COLS['match_date'], COLS['league'], COLS['home_team'], COLS['away_team']], keep='last')
df_final.to_csv('prediction_results.csv', index=False)
print(f"Success! Results saved. Total records: {len(df_final)}")