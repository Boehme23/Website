import pandas as pd
import sqlite3
import os


def determine_winner(row):
    # Ensure the Result is a string and contains the delimiter ':'
    res = str(row['Result'])
    if ':' not in res:
        return 'Unknown'

    try:
        # Split '1:0' into [1, 0]
        home_score, away_score = map(int, res.split(':'))

        if home_score > away_score:
            return row['Home']
        elif away_score > home_score:
            return row['Away']
        else:
            return 'Draw'
    except ValueError:
        return 'Invalid Score'


def convert_csv_to_db(csv_files, db_name):
    conn = sqlite3.connect(db_name)

    for csv_file in csv_files:
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)

            # Clean column names
            df.columns = [c.replace(' ', '_').replace('.', '_').strip() for c in df.columns]

            # --- CUSTOM LOGIC FOR SCHEDULE TABLE ---
            table_name = os.path.splitext(csv_file)[0]
            if table_name == 'All_Schedule_Combined':
                print(f"Adding 'game_winner' column to {table_name}...")
                # We apply the function to every row
                df['game_winner'] = df.apply(determine_winner, axis=1)
            # ----------------------------------------

            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"Successfully converted '{csv_file}' to table '{table_name}'")
        else:
            print(f"File not found: {csv_file}")

    conn.close()
    print("Database conversion complete.")


# Configuration
files_to_process = ['prediction_results.csv', 'All_Schedule_Combined.csv']
output_database = 'my_data.db'

convert_csv_to_db(files_to_process, output_database)