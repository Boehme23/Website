import pandas as pd
from thefuzz import process, fuzz
import os

# 1. Manual Overrides (Keys are 'Wrong/Short', Values are 'Target/Reference')
MANUAL_MAP = {
    'Wolves': 'Wolverhampton Wanderers',
    'Man Utd': 'Manchester United',
    'Spurs': 'Tottenham Hotspur',
    'Manchester Utd': 'Manchester United',
    'Leeds': 'Leeds United FC',
    'PSG': 'FC Paris Saint-Germain',
    'Rennes': 'Stade Rennais FC',
    'AFS': 'Avs - Futebol SAD',
    'Atlético de Madrid': 'Atlético',
    'Atlético': 'Atlético Madrid',
}


def fix_and_save_teams(threshold=35):
    try:
        # --- 1. Load Reference Data ---
        if not os.path.exists("All_Leagues_Combined.csv"):
            print("Error: Reference file 'All_Leagues_Combined.csv' not found.")
            return

        df_leagues = pd.read_csv("All_Leagues_Combined.csv")
        # Ensure we are getting strings and removing whitespace
        reference_teams = [str(x).strip() for x in df_leagues['Clube'].unique() if pd.notna(x)]

        print(f"DEBUG: Found {len(reference_teams)} unique teams in Reference File.")

        files_to_fix = ["All_Schedule_Combined.csv", "All_Proximos_Jogos.csv"]
        all_changes = []

        for file_name in files_to_fix:
            if not os.path.exists(file_name):
                print(f"Skipping {file_name}: File not found.")
                continue

            print(f"\n--- Processing File: {file_name} ---")
            df = pd.read_csv(file_name)

            home_col = next((c for c in ['Home', 'Casa', 'Clube'] if c in df.columns), None)
            away_col = next((c for c in ['Away', 'Fora'] if c in df.columns), None)

            if not home_col or not away_col:
                print(f"Warning: Could not find team columns in {file_name}.")
                continue

            def get_best_match(team_name):
                team_str = str(team_name).strip()
                if not team_str or team_str.lower() == 'nan':
                    return team_name

                # A. Check Manual Map (CASE-INSENSITIVE)
                # This ensures 'wolves' matches 'Wolves' in our dictionary
                for shortcut, full_name in MANUAL_MAP.items():
                    if team_str.lower() == shortcut.lower():
                        return full_name

                # B. Check Case-Insensitive Direct Match in Reference
                for ref in reference_teams:
                    if team_str.lower() == ref.lower():
                        return ref

                # C. Fuzzy Match
                best_match, score = process.extractOne(team_str, reference_teams, scorer=fuzz.token_sort_ratio)
                return best_match if score >= threshold else team_str

            # Capture state before applying
            original_unique = set(df[home_col].unique()) | set(df[away_col].unique())

            # Apply the mapping
            df[home_col] = df[home_col].apply(get_best_match)
            df[away_col] = df[away_col].apply(get_best_match)

            # Log actual changes
            for name in original_unique:
                fixed_name = get_best_match(name)
                if str(name).strip() != str(fixed_name).strip():
                    all_changes.append({
                        'File': file_name,
                        'Original_Name': name,
                        'Corrected_Name': fixed_name
                    })

            # Save the fixed file
            df.to_csv(file_name, index=False, encoding='utf-8-sig')

            # Recalculate mismatches for the console report
            new_unique = set(df[home_col].unique()) | set(df[away_col].unique())
            mismatches_before = [t for t in original_unique if t not in reference_teams]
            mismatches_after = [t for t in new_unique if t not in reference_teams]
            print(f"Result: Mismatches reduced from {len(mismatches_before)} to {len(mismatches_after)}")

        # --- 2. Save the Change Log ---
        if all_changes:
            df_log = pd.DataFrame(all_changes).drop_duplicates(subset=['Original_Name', 'Corrected_Name'])
            df_log.to_csv("team_name_changes_log.csv", index=False, encoding='utf-8-sig')
            print(f"\nSuccess! Summary of changes saved to 'team_name_changes_log.csv'")
        else:
            print("\nNo names were changed.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    fix_and_save_teams()