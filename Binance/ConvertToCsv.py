import sqlite3
import pandas as pd

# 1. Connect to the Binance history database
db_path = 'binance_history.db'
conn = sqlite3.connect(db_path)

# 2. Get a list of all table names (one for each coin)
# We exclude 'sqlite_sequence' which is an internal system table
query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
tables = pd.read_sql_query(query, conn)['name'].tolist()
all_data = []


# 3. Loop through tables and read data
df = pd.read_sql_query(f'SELECT * FROM "historico_precos"', conn)
all_data.append(df)


# 4. Concatenate all DataFrames into one
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)

    # 5. Export to CSV
    output_file = 'all_crypto_history.csv'
    final_df.to_csv(output_file, index=False)
    print(f"Success! All data saved to {output_file}")
else:
    print("No tables found in the database.")

# Close connection
conn.close()