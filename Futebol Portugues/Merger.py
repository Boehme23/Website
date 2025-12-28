import pandas as pd
import os

# 1. Configuration
# The same list you used in your scraper
ligas = [
    ('ligue-1', 'FR1'),
    ('liga-nos', 'PO1'),
    ('eredivisie', 'NL1'),
    ('premier-league', 'GB1'),
    ('laliga', 'ES1'),
    ('bundesliga', 'L1')
]

name= ''
# Define how your individual files are named.
# {name} will be replaced by 'ligue-1', 'liga-nos', etc.
# If your files are just named 'ligue-1.csv', change this to: f"{name}.csv"
FILENAME_PATTERN = "Futebol_{name}.csv"

OUTPUT_FILE = "All_Leagues_Combined.csv"


def merge_csv_files():
    all_dataframes = []

    print(f"--- Starting Merge Process ---")

    for league_name, league_code in ligas:
        # Construct the expected filename
        file_path = FILENAME_PATTERN.format(name=league_code)

        # Check if file exists to avoid crashing
        if os.path.exists(file_path):
            try:
                # 1. Read the CSV
                df = pd.read_csv(file_path)

                # 2. Add the Identifier Column
                # You can use the name ('ligue-1') or the code ('FR1')
                df['League'] = league_code

                # Optional: Add a specific Round column if you want to hardcode it
                # df['Round'] = 15

                # 3. Add to our list
                all_dataframes.append(df)
                print(f"[OK] Loaded {file_path} ({len(df)} rows)")

            except Exception as e:
                print(f"[ERROR] Could not read {file_path}: {e}")
        else:
            print(f"[WARNING] File not found: {file_path}")

    # 4. Concatenate (Append) all dataframes
    if all_dataframes:
        final_df = pd.concat(all_dataframes, ignore_index=True)

        # Reorder columns to put League first (Optional)
        cols = ['League'] + [c for c in final_df.columns if c != 'League']
        final_df = final_df[cols]

        # 5. Save Final File
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSUCCESS! Merged {len(all_dataframes)} files into '{OUTPUT_FILE}'.")
        print(f"Total Rows: {len(final_df)}")
        print(final_df.head())
    else:
        print("\nNo files were loaded. Nothing to merge.")


if __name__ == "__main__":
    merge_csv_files()