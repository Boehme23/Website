import pandas as pd
from thefuzz import process, fuzz

# 1. Manual Overrides (Add any other stubborn mismatches here)
MANUAL_MAP = {
    'Wolves': 'Wolverhampton Wanderers',
    'Man Utd': 'Manchester United',
    'Spurs': 'Tottenham Hotspur'
}


def fix_and_save_teams(threshold=35):
    try:
        # Load Reference
        df_leagues = pd.read_csv("All_Leagues_Combined.csv")
        reference_teams = list(df_leagues['Clube'].unique())

        files_to_fix = ["All_Schedule_Combined.csv", "All_Proximos_Jogos.csv"]

        for file_name in files_to_fix:
            print(f"\n--- Fixing File: {file_name} ---")
            df = pd.read_csv(file_name)

            # Identify columns
            home_col = next((c for c in ['Home', 'Casa', 'Clube'] if c in df.columns), None)
            away_col = next((c for c in ['Away', 'Fora'] if c in df.columns), None)

            if not home_col or not away_col: continue

            def get_best_match(team_name):
                team_str = str(team_name).strip()

                # Check Manual Map first
                if team_str in MANUAL_MAP:
                    return MANUAL_MAP[team_str]

                # If already correct, return it
                if team_str in reference_teams:
                    return team_str

                # Fuzzy Match
                best_match, score = process.extractOne(team_str, reference_teams, scorer=fuzz.token_sort_ratio)

                if score >= threshold:
                    return best_match
                return team_str  # Keep original if no good match

            # Apply the fix to both columns
            original_unique = set(df[home_col].unique()) | set(df[away_col].unique())

            df[home_col] = df[home_col].apply(get_best_match)
            df[away_col] = df[away_col].apply(get_best_match)

            # Save the cleaned file
            df.to_csv(file_name, index=False, encoding='utf-8-sig')

            new_unique = set(df[home_col].unique()) | set(df[away_col].unique())
            print(
                f"Fixed! Mismatches reduced from {len(original_unique - set(reference_teams))} to {len(new_unique - set(reference_teams))}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    fix_and_save_teams()