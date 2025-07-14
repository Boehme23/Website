import logging
import sqlite3

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# --- Setup Logging ---
# Ensures logging is configured only once.
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db_file = '../Fort/fort.db'
conn = None  # Initialize conn to None
try:
    # --- Database Connection and Data Loading ---
    conn = sqlite3.connect(db_file)
    logging.info(f"Successfully connected to database '{db_file}'")

    # Load data and ensure the 'date' column is in datetime format for resampling
    df_read_sql = pd.read_sql_query("SELECT * FROM products;", conn)
    df_read_sql['date'] = pd.to_datetime(df_read_sql['date'])
    logging.info("\n--- DataFrame loaded successfully ---")

    # --- Data Pivoting for Daily Analysis ---
    pivot_df = df_read_sql.pivot_table(index='name', columns='date', values='price', fill_value=0)
    logging.info("\n--- Initial Pivot Table (before filling missing values): ---")
    logging.info(pivot_df.head())

    # --- Forward Fill Logic ---
    logging.info("\n--- Filling in missing (0) values with the last known price... ---")
    pivot_df.replace(0, np.nan, inplace=True)
    pivot_df.ffill(axis=1, inplace=True)
    pivot_df.fillna(0, inplace=True)
    logging.info("\n--- Pivot Table after forward fill: ---")
    logging.info(pivot_df.head())

    # --- Exclude rows that still contain zero values ---
    logging.info("\n--- Filtering out rows that contain zero values... ---")
    initial_rows = len(pivot_df)
    pivot_df = pivot_df.loc[~(pivot_df == 0).any(axis=1)]
    final_rows = len(pivot_df)
    logging.info(f"Removed {initial_rows - final_rows} rows containing zero. {final_rows} rows remain.")
    logging.info("-" * 30)

    # --- Main Processing Block ---
    if not pivot_df.empty:
        # --- Percentage Change Calculation (on daily data) ---
        if len(pivot_df.columns) >= 2:
            old_date_col = pivot_df.columns[-2]
            new_date_col = pivot_df.columns[-1]
            logging.info(
                f"\nCalculating percentage change between '{old_date_col.strftime('%Y-%m-%d')}' and '{new_date_col.strftime('%Y-%m-%d')}'...")

            old_values = pivot_df[old_date_col]
            new_values = pivot_df[new_date_col]

            pivot_df['%'] = np.where(
                old_values > 0,
                (new_values - old_values) * 100 / old_values,
                0
            ).round(2)

            # Sort by the daily percentage change
            pivot_df.sort_values(by='%', ascending=False, inplace=True)
            logging.info("\n--- Daily Pivot Table with Percentage Change, Sorted (head): ---")
            logging.info(pivot_df.head())
        else:
            logging.warning("\nNot enough data to calculate daily percentage change.")
            if '%' not in pivot_df.columns:
                pivot_df['%'] = 0

        # --- Prepare data for weekly and monthly aggregation ---
        # Melt the forward-filled pivot table back into a long format for easier resampling
        df_for_resampling = pivot_df.drop(columns=['%'])  # Drop daily percentage before resampling
        df_filled_long = df_for_resampling.reset_index().melt(
            id_vars='name', var_name='date', value_name='price'
        )
        df_filled_long['date'] = pd.to_datetime(df_filled_long['date'])

        # --- Calculate Weekly Average Price ---
        logging.info("\n--- Calculating weekly average price based on forward-filled data... ---")
        df_filled_long['week_ending'] = df_filled_long['date'] + pd.to_timedelta(
            6 - df_filled_long['date'].dt.dayofweek, unit='d'
        )
        weekly_avg_df = df_filled_long.groupby(['name', 'week_ending'])['price'].mean().round(2)
        weekly_avg_df = weekly_avg_df.unstack(level='week_ending')
        weekly_avg_df.columns = [f"Week_of_{col.strftime('%Y-%m-%d')}" for col in weekly_avg_df.columns]
        logging.info("\n--- Weekly Average Prices (head): ---")
        logging.info(weekly_avg_df.head())

        # --- Calculate Week-over-Week Variation for ALL Weeks ---
        weekly_pct_change_df = pd.DataFrame()  # Initialize as empty
        sector_weekly_variation_df = pd.DataFrame()  # Initialize as empty
        if not weekly_avg_df.empty and len(weekly_avg_df.columns) >= 2:
            logging.info("\n--- Calculating week-over-week percentage variation for all weeks... ---")
            weekly_pct_change_df = weekly_avg_df.pct_change(axis=1).round(4) * 100
            weekly_pct_change_df = weekly_pct_change_df.iloc[:, 1:]  # Remove first NaN column
            logging.info("\n--- Weekly Percentage Changes (head): ---")
            logging.info(weekly_pct_change_df.head())

            # --- Calculate the average variation across all products for each week ---
            logging.info("\n--- Calculating average weekly variation across all products... ---")
            overall_weekly_variation = weekly_pct_change_df.mean().round(2)
            overall_weekly_variation.name = 'Overall Market'  # Give the series a name

            # --- Calculate the average variation grouped by sector ---
            if 'sector' in df_read_sql.columns:
                logging.info("\n--- Calculating average weekly variation by sector... ---")
                sector_map = df_read_sql[['name', 'sector']].drop_duplicates().set_index('name')['sector']
                sector_pct_change_df = weekly_pct_change_df.join(sector_map)
                sector_weekly_variation_df = sector_pct_change_df.groupby('sector').mean().round(2)
                sector_weekly_variation_df = pd.concat(
                    [sector_weekly_variation_df, overall_weekly_variation.to_frame().T])
                logging.info("\n--- Sector-Level and Overall Average Weekly Variation: ---")
                logging.info(sector_weekly_variation_df)
            else:
                logging.warning("\n'sector' column not found in data. Creating overall market weekly report instead.")
                sector_weekly_variation_df = overall_weekly_variation.to_frame().T
        else:
            logging.warning("\nNot enough weekly data (fewer than 2 weeks) to calculate percentage variation.")

        # --- NEW: Calculate Monthly Average Price ---
        logging.info("\n--- Calculating monthly average price based on forward-filled data... ---")
        # Use .to_period('M') to group by month
        monthly_avg_df = df_filled_long.groupby(['name', df_filled_long['date'].dt.to_period('M')])[
            'price'].mean().round(2)
        monthly_avg_df = monthly_avg_df.unstack(level='date')  # Unstack to get months as columns
        # Format column names for readability
        monthly_avg_df.columns = [f"Month_of_{col.strftime('%Y-%m')}" for col in monthly_avg_df.columns]
        logging.info("\n--- Monthly Average Prices (head): ---")
        logging.info(monthly_avg_df.head())

        # --- NEW: Calculate Month-over-Month Variation for ALL Months ---
        monthly_pct_change_df = pd.DataFrame()  # Initialize as empty
        sector_monthly_variation_df = pd.DataFrame()  # Initialize as empty
        if not monthly_avg_df.empty and len(monthly_avg_df.columns) >= 2:
            logging.info("\n--- Calculating month-over-month percentage variation for all months... ---")
            monthly_pct_change_df = monthly_avg_df.pct_change(axis=1).round(4) * 100
            monthly_pct_change_df = monthly_pct_change_df.iloc[:, 1:]  # Remove first NaN column
            logging.info("\n--- Monthly Percentage Changes (head): ---")
            logging.info(monthly_pct_change_df.head())

            # --- Calculate the average variation across all products for each month ---
            logging.info("\n--- Calculating average monthly variation across all products... ---")
            overall_monthly_variation = monthly_pct_change_df.mean().round(2)
            overall_monthly_variation.name = 'Overall Market'  # Give the series a name

            # --- Calculate the average variation grouped by sector for monthly data ---
            if 'sector' in df_read_sql.columns:
                logging.info("\n--- Calculating average monthly variation by sector... ---")
                # Reuse sector_map created for weekly calculations
                sector_monthly_pct_change_df = monthly_pct_change_df.join(sector_map)
                sector_monthly_variation_df = sector_monthly_pct_change_df.groupby('sector').mean().round(2)
                sector_monthly_variation_df = pd.concat(
                    [sector_monthly_variation_df, overall_monthly_variation.to_frame().T])
                logging.info("\n--- Sector-Level and Overall Average Monthly Variation: ---")
                logging.info(sector_monthly_variation_df)
            else:
                logging.warning("\n'sector' column not found in data. Creating overall market monthly report instead.")
                sector_monthly_variation_df = overall_monthly_variation.to_frame().T
        else:
            logging.warning("\nNot enough monthly data (fewer than 2 months) to calculate percentage variation.")

        logging.info("-" * 30)

        # --- Save to Excel ---
        daily_excel_file = '../Fort/Fort_prices_daily_analysis.xlsx'
        pivot_df.to_excel(daily_excel_file, index=True)
        logging.info(f"\nSuccessfully saved daily analysis to '{daily_excel_file}'")

        if not weekly_avg_df.empty:
            weekly_avg_excel_file = '../Fort/Fort_prices_weekly_avg.xlsx'
            weekly_avg_df.to_excel(weekly_avg_excel_file, index=True)
            logging.info(f"\nSuccessfully saved weekly average prices to '{weekly_avg_excel_file}'")

        if not weekly_pct_change_df.empty:
            weekly_pct_change_excel_file = '../Fort/Fort_prices_weekly_pct_change.xlsx'
            weekly_pct_change_df.to_excel(weekly_pct_change_excel_file, index=True)
            logging.info(f"\nSuccessfully saved weekly percentage changes to '{weekly_pct_change_excel_file}'")

        # NEW: Save Monthly Average and Percentage Change files
        if not monthly_avg_df.empty:
            monthly_avg_excel_file = '../Fort/Fort_prices_monthly_avg.xlsx'
            monthly_avg_df.to_excel(monthly_avg_excel_file, index=True)
            logging.info(f"\nSuccessfully saved monthly average prices to '{monthly_avg_excel_file}'")

        if not monthly_pct_change_df.empty:
            monthly_pct_change_excel_file = '../Fort/Fort_prices_monthly_pct_change.xlsx'
            monthly_pct_change_df.to_excel(monthly_pct_change_excel_file, index=True)
            logging.info(f"\nSuccessfully saved monthly percentage changes to '{monthly_pct_change_excel_file}'")

        # Save the combined sector-level and overall weekly variation
        sector_weekly_excel_file = '../static/images/Fort_sector_weekly_variation.xlsx'
        if not sector_weekly_variation_df.empty:
            sector_weekly_variation_df.to_excel(sector_weekly_excel_file, index=True)
            logging.info(
                f"\nSuccessfully saved combined sector and overall weekly variation to '{sector_weekly_excel_file}'")

        # NEW: Save the combined sector-level and overall monthly variation
        sector_monthly_excel_file = '../static/images/Fort_sector_monthly_variation.xlsx'
        if not sector_monthly_variation_df.empty:
            sector_monthly_variation_df.to_excel(sector_monthly_excel_file, index=True)
            logging.info(
                f"\nSuccessfully saved combined sector and overall monthly variation to '{sector_monthly_excel_file}'")

        # --- Gerar e Salvar o Gráfico Semanal (com Destaque) ---
        if not sector_weekly_variation_df.empty:
            logging.info("\n--- Generating weekly sector performance chart... ---")
            try:
                plot_df_weekly = sector_weekly_variation_df.transpose()
                fig_weekly, ax_weekly = plt.subplots(figsize=(15, 8))
                plot_df_weekly.index = plot_df_weekly.index.str.replace('Week_of_', '', regex=False)

                for column in plot_df_weekly.columns:
                    if column == 'Overall Market':
                        ax_weekly.plot(plot_df_weekly.index, plot_df_weekly[column], marker='o', linestyle='--',
                                       label=column, color='black', linewidth=2.5, zorder=10)
                    else:
                        ax_weekly.plot(plot_df_weekly.index, plot_df_weekly[column], marker='.', linestyle='-',
                                       label=column, linewidth=1.5, alpha=0.8)

                ax_weekly.set_title('Inflação Semanal por Setor e Mercado Geral', fontsize=16, pad=20)
                ax_weekly.set_ylabel('Inflação Semanal (%)', fontsize=12)
                ax_weekly.set_xlabel('Semana Terminada em', fontsize=12)
                ax_weekly.axhline(0, color='grey', linestyle='--', linewidth=0.8)
                plt.xticks(rotation=30, ha="right")
                ax_weekly.legend(title='Setor / Mercado', bbox_to_anchor=(1.02, 1), loc='upper left')
                ax_weekly.grid(True, which='both', linestyle='--', linewidth=0.5)
                ax_weekly.yaxis.set_major_formatter(mticker.PercentFormatter())
                plt.tight_layout(rect=[0, 0, 0.85, 1])
                chart_file_name_weekly = '../static/images/Fort_sector_weekly_variation_chart.png'
                plt.savefig(chart_file_name_weekly, dpi=300, bbox_inches='tight')
                logging.info(f"\nSuccessfully saved weekly chart to '{chart_file_name_weekly}'")
                plt.close(fig_weekly)

            except Exception as e:
                logging.error(f"Could not generate or save the weekly chart. Error: {e}")

        # --- NEW: Gerar e Salvar o Gráfico Mensal (com Destaque) ---
        if not sector_monthly_variation_df.empty:
            logging.info("\n--- Generating monthly sector performance chart... ---")
            try:
                plot_df_monthly = sector_monthly_variation_df.transpose()
                fig_monthly, ax_monthly = plt.subplots(figsize=(15, 8))
                plot_df_monthly.index = plot_df_monthly.index.str.replace('Month_of_', '', regex=False)

                for column in plot_df_monthly.columns:
                    if column == 'Overall Market':
                        ax_monthly.plot(plot_df_monthly.index, plot_df_monthly[column], marker='o', linestyle='--',
                                        label=column, color='black', linewidth=2.5, zorder=10)
                    else:
                        ax_monthly.plot(plot_df_monthly.index, plot_df_monthly[column], marker='.', linestyle='-',
                                        label=column, linewidth=1.5, alpha=0.8)

                ax_monthly.set_title('Inflação Mensal por Setor e Mercado Geral', fontsize=16, pad=20)
                ax_monthly.set_ylabel('Inflação Mensal (%)', fontsize=12)
                ax_monthly.set_xlabel('Mês', fontsize=12)
                ax_monthly.axhline(0, color='grey', linestyle='--', linewidth=0.8)
                plt.xticks(rotation=30, ha="right")
                ax_monthly.legend(title='Setor / Mercado', bbox_to_anchor=(1.02, 1), loc='upper left')
                ax_monthly.grid(True, which='both', linestyle='--', linewidth=0.5)
                ax_monthly.yaxis.set_major_formatter(mticker.PercentFormatter())
                plt.tight_layout(rect=[0, 0, 0.85, 1])
                chart_file_name_monthly = '../static/images/Fort_sector_monthly_variation_chart.png'
                plt.savefig(chart_file_name_monthly, dpi=300, bbox_inches='tight')
                logging.info(f"\nSuccessfully saved monthly chart to '{chart_file_name_monthly}'")
                plt.close(fig_monthly)

            except Exception as e:
                logging.error(f"Could not generate or save the monthly chart. Error: {e}")

        # Table Chart for weekly variation
        if not sector_weekly_variation_df.empty:
            logging.info("\n--- Generating weekly variation table image... ---")
            data = sector_weekly_variation_df
            df = pd.DataFrame(data)
            row_labels = df.index.tolist()
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.axis('off')
            ax.set_frame_on(False)
            table_data = df.values
            col_labels = ['Sector'] + df.columns.tolist()
            full_table_data = [[label] + row.tolist() for label, row in zip(row_labels, table_data)]

            table = ax.table(cellText=full_table_data,
                             colLabels=col_labels,
                             cellLoc='center',
                             loc='center')
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.2, 1.2)
            ax.set_title('Fort Prices Weekly Percentage Change by Sector', fontsize=14, pad=20)
            plt.tight_layout()
            plt.savefig('../static/images/fort_prices_weekly_table.png', bbox_inches='tight', dpi=300)
            logging.info(
                f"\nSuccessfully saved weekly variation table to '../static/images/fort_prices_weekly_table.png'")
            plt.close(fig)  # Close the figure to free memory
        else:
            logging.warning("Weekly variation DataFrame is empty. Skipping weekly table generation.")

        # NEW: Table Chart for monthly variation
        if not sector_monthly_variation_df.empty:
            logging.info("\n--- Generating monthly variation table image... ---")
            data = sector_monthly_variation_df
            df = pd.DataFrame(data)
            row_labels = df.index.tolist()
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.axis('off')
            ax.set_frame_on(False)
            table_data = df.values
            col_labels = ['Sector'] + df.columns.tolist()
            full_table_data = [[label] + row.tolist() for label, row in zip(row_labels, table_data)]

            table = ax.table(cellText=full_table_data,
                             colLabels=col_labels,
                             cellLoc='center',
                             loc='center')
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.2, 1.2)
            ax.set_title('Fort Prices Monthly Percentage Change by Sector', fontsize=14, pad=20)
            plt.tight_layout()
            plt.savefig('../static/images/fort_prices_monthly_table.png', bbox_inches='tight', dpi=300)
            logging.info(
                f"\nSuccessfully saved monthly variation table to '../static/images/fort_prices_monthly_table.png'")
            plt.close(fig)  # Close the figure to free memory
        else:
            logging.warning("Monthly variation DataFrame is empty. Skipping monthly table generation.")

    else:
        logging.warning("DataFrame is empty after filtering. No Excel files or charts will be generated.")

except sqlite3.Error as e:
    logging.error(f"An SQLite error occurred: {e}")
except FileNotFoundError:
    logging.error(f"Error: The database file was not found at '{db_file}'")
except Exception as e:
    logging.error(f"An unexpected error occurred: {e}", exc_info=True)
finally:
    # --- Close Connection ---
    if conn:
        conn.close()
        logging.info("\nDatabase connection closed.")

# Note: plt.show() should only be used if you are running this script interactively
# and want to see the plots immediately. For automated scripts (e.g., in a server
# environment or cron job), you usually save the figures and don't call plt.show().
# I've commented it out as per standard practice for server-side generation.
# plt.show()
