import datetime
import sqlite3

import numpy as np
import pandas as pd

db_file = './Fort/fort.db'

try:
    conn = sqlite3.connect(db_file)

    print(f"--- Attempting to load data from '{db_file}' using direct cursor operations ---")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products;")

    rows = cursor.fetchall()
    print("\n--- Raw data fetched by cursor.fetchall() (first few rows): ---")
    # Print only the first few rows if 'rows' is very large
    for i, row in enumerate(rows):
        if i < 5:  # Print first 5 rows for inspection
            print(row)
        else:
            break
    if len(rows) > 5:
        print("...")  # Indicate that more rows exist

    column_names = [description[0] for description in cursor.description]
    print(f"\n--- Column names identified by cursor.description: ---")
    print(column_names)

    df_manual = pd.DataFrame(rows, columns=column_names)
    print("\n--- DataFrame created manually (head): ---")
    # Pandas sometimes truncates display for many columns.
    # To see all columns, you can adjust display options temporarily.
    with pd.option_context('display.max_columns', None):
        print(df_manual.head())

    print("\n--- Verifying total columns in manually created DataFrame: ---")
    print(f"Number of columns in df_manual: {len(df_manual.columns)}")
    print(f"df_manual columns: {df_manual.columns.tolist()}")

    print(f"\n--- Attempting to load data using pd.read_sql_query (recommended) ---")
    # pd.read_sql_query is often more reliable and efficient for this task.
    df_read_sql = pd.read_sql_query("SELECT * FROM products;", conn)

    print("\n--- DataFrame created with pd.read_sql_query (head): ---")
    with pd.option_context('display.max_columns', None):
        print(df_read_sql.head())

    print("\n--- Verifying total columns in pd.read_sql_query DataFrame: ---")
    print(f"Number of columns in df_read_sql: {len(df_read_sql.columns)}")
    print(f"df_read_sql columns: {df_read_sql.columns.tolist()}")

    # Create a pivot table to get 'in' and 'out' quantities side-by-side for each name
    # Fill NaN with 0 for cases where a product only has 'in' or 'out'
    pivot_df = df_read_sql.pivot_table(index='name', columns='date', values='price', fill_value=0)

    print("\nPivot Table (quantities by type):")
    print(pivot_df)
    print("-" * 30)
    old_values = pivot_df['2025-06-06']
    new_values = pivot_df[datetime.date.today().strftime('%Y-%m-%d')]
    condition_for_zero_percent = (old_values == 0) | (new_values == 0)
    # Calculate the difference: 'in' - 'out'
    pivot_df['%'] = np.where(
        condition_for_zero_percent,
        0,  # Value if the condition is True
        (new_values - old_values) / old_values  # Value if the condition is False
    )
    pivot_df = pivot_df.sort_values(by='%', ascending=False)
    print("\nPivot Table with Net Quantity:")
    print(pivot_df)
    print("-" * 30)
except sqlite3.Error as e:
    print(f"An SQLite error occurred: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    if conn:
        conn.close()
        print("\nDatabase connection closed.")

# Define the output Excel filename
excel_file_name = 'Fort_prices.xlsx'

try:
    # Save the DataFrame to an Excel file
    # index=False prevents Pandas from writing the DataFrame index as a column in Excel
    pivot_df.to_excel(excel_file_name, index=True)
    print(f"Successfully saved DataFrame to '{excel_file_name}'")

except Exception as e:
    print(f"An error occurred while saving the Excel file: {e}")
