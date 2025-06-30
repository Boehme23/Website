import logging
import sqlite3

import matplotlib
# --- NOVA IMPORTAÇÃO ---
# Adiciona a biblioteca para criar gráficos
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

        # --- Calculate Weekly Average Price ---
        logging.info("\n--- Calculating weekly average price based on forward-filled data... ---")
        df_for_melting = pivot_df.drop(columns=['%'])
        df_filled_long = df_for_melting.reset_index().melt(
            id_vars='name', var_name='date', value_name='price'
        )
        df_filled_long['date'] = pd.to_datetime(df_filled_long['date'])
        df_filled_long['week_ending'] = df_filled_long['date'] + pd.to_timedelta(
            6 - df_filled_long['date'].dt.dayofweek, unit='d'
        )
        weekly_avg_df = df_filled_long.groupby(['name', 'week_ending'])['price'].mean().round(2)
        weekly_avg_df = weekly_avg_df.unstack(level='week_ending')
        weekly_avg_df.columns = [f"Week_of_{col.strftime('%Y-%m-%d')}" for col in weekly_avg_df.columns]
        logging.info("\n--- Weekly Average Prices (head): ---")
        logging.info(weekly_avg_df.head())

        # --- Calculate Week-over-Week Variation for ALL Weeks ---
        if not weekly_avg_df.empty and len(weekly_avg_df.columns) >= 2:
            logging.info("\n--- Calculating week-over-week percentage variation for all weeks... ---")
            weekly_pct_change_df = weekly_avg_df.pct_change(axis=1).round(4) * 100
            weekly_pct_change_df = weekly_pct_change_df.iloc[:, 1:]
            logging.info("\n--- Weekly Percentage Changes (head): ---")
            logging.info(weekly_pct_change_df.head())

            # --- Calculate the average variation across all products for each week ---
            logging.info("\n--- Calculating average weekly variation across all products... ---")
            overall_weekly_variation = weekly_pct_change_df.mean().round(2)
            # Give the series a name which will become the index of the new row
            overall_weekly_variation.name = 'Overall Market'

            # --- Calculate the average variation grouped by sector ---
            # Check if the 'sector' column exists in the original data
            if 'sector' in df_read_sql.columns:
                logging.info("\n--- Calculating average weekly variation by sector... ---")
                # Create a mapping from product name to sector. Drop duplicates to be safe.
                sector_map = df_read_sql[['name', 'sector']].drop_duplicates().set_index('name')['sector']

                # Join the sector information to the weekly percentage change DataFrame
                sector_pct_change_df = weekly_pct_change_df.join(sector_map)

                # Group by sector and calculate the mean for each week
                sector_weekly_variation_df = sector_pct_change_df.groupby('sector').mean().round(2)

                # --- Add the overall market variation as a new row ---
                # Use pd.concat to add the overall variation series as a new row.
                sector_weekly_variation_df = pd.concat(
                    [sector_weekly_variation_df, overall_weekly_variation.to_frame().T])

                logging.info("\n--- Sector-Level and Overall Average Weekly Variation: ---")
                logging.info(sector_weekly_variation_df)
            else:
                logging.warning("\n'sector' column not found in data. Creating overall market report instead.")
                # If no sectors, the report is just the overall market variation.
                sector_weekly_variation_df = overall_weekly_variation.to_frame().T

        else:
            logging.warning("\nNot enough weekly data (fewer than 2 weeks) to calculate percentage variation.")
            weekly_pct_change_df = pd.DataFrame()
            sector_weekly_variation_df = pd.DataFrame()

        logging.info("-" * 30)

        tablefigure = matplotlib.pyplot.table(sector_weekly_variation_df)

        # --- Save to Excel ---

        daily_excel_file = '../Fort/Fort_prices_daily_analysis.xlsx'
        pivot_df.to_excel(daily_excel_file, index=True)
        logging.info(f"\nSuccessfully saved daily analysis to '{daily_excel_file}'")

        if not weekly_avg_df.empty:
            weekly_avg_excel_file = ('..'
                                     '/Fort/Fort_prices_weekly_avg.xlsx')
            weekly_avg_df.to_excel(weekly_avg_excel_file, index=True)
            logging.info(f"\nSuccessfully saved weekly average prices to '{weekly_avg_excel_file}'")

        if not weekly_pct_change_df.empty:
            weekly_pct_change_excel_file = '../Fort/Fort_prices_weekly_pct_change.xlsx'
            weekly_pct_change_df.to_excel(weekly_pct_change_excel_file, index=True)
            logging.info(f"\nSuccessfully saved weekly percentage changes to '{weekly_pct_change_excel_file}'")

        # Save the new combined sector-level and overall weekly variation
        sector_excel_file = '../static/images/Fort_sector_weekly_variation.xlsx'
        if not sector_weekly_variation_df.empty:
            sector_weekly_variation_df.to_excel(sector_excel_file, index=True)
            logging.info(f"\nSuccessfully saved combined sector and overall weekly variation to '{sector_excel_file}'")

            # --- Gerar e Salvar o Gráfico (com Destaque) ---
            logging.info("\n--- Generating sector performance chart... ---")
            try:
                # Transpõe o DataFrame para que as semanas fiquem no eixo X
                plot_df = sector_weekly_variation_df.transpose()

                # Cria a figura e os eixos do gráfico com um tamanho maior
                fig, ax = plt.subplots(figsize=(15, 8))

                # Remove o prefixo "Week_of_" para um eixo X mais limpo ---
                plot_df.index = plot_df.index.str.replace('Week_of_', '', regex=False)

                # Plota a performance de cada setor/mercado
                for column in plot_df.columns:

                    if column == 'Overall Market':
                        # Estilo de destaque para o mercado geral
                        ax.plot(plot_df.index, plot_df[column], marker='o', linestyle='--',
                                label=column, color='black', linewidth=2.5, zorder=10)
                    else:
                        # Estilo padrão para os outros setores
                        ax.plot(plot_df.index, plot_df[column], marker='.', linestyle='-',
                                label=column, linewidth=1.5, alpha=0.8)

                # Formatação do gráfico para melhor clareza
                ax.set_title('Inflação semanal por Setor e Mercado Geral', fontsize=16, pad=20)
                ax.set_ylabel('Inflação Semanal (%)', fontsize=12)
                ax.set_xlabel('Semana Terminada em', fontsize=12)

                # Adiciona uma linha horizontal em y=0 como referência
                ax.axhline(0, color='grey', linestyle='--', linewidth=0.8)

                # Melhora a legibilidade dos rótulos do eixo X
                plt.xticks(rotation=30, ha="right")

                # Adiciona a legenda
                ax.legend(title='Setor / Mercado', bbox_to_anchor=(1.02, 1), loc='upper left')

                # Adiciona grades para facilitar a leitura
                ax.grid(True, which='both', linestyle='--', linewidth=0.5)

                # Formata o eixo Y para mostrar o símbolo de '%'
                ax.yaxis.set_major_formatter(mticker.PercentFormatter())

                # Ajusta o layout para evitar que os rótulos sejam cortados
                plt.tight_layout(rect=[0, 0, 0.85, 1])  # Ajusta o retângulo para dar espaço à legenda

                # Salva a figura
                chart_file_name = '../static/images/Fort_sector_variation_chart.png'
                plt.savefig(chart_file_name, dpi=300, bbox_inches='tight')
                logging.info(f"\nSuccessfully saved chart to '{chart_file_name}'")
                plt.close(fig)  # Fecha a figura para liberar memória

            except Exception as e:
                logging.error(f"Could not generate or save the chart. Error: {e}")

            # table chart
            data = sector_weekly_variation_df
            df = pd.DataFrame(data)

            # Extract sector names (index of the DataFrame)
            row_labels = df.index.tolist()

            # 2. Create a figure and axes
            fig, ax = plt.subplots(figsize=(10, 6))  # Adjust figsize as needed for your table's content

            # 3. Hide axes for a cleaner table look
            ax.axis('off')  # Hides x and y axis
            ax.set_frame_on(False)  # Hides the box around the plot

            # 4. Add the table to the axes
            # You need to combine the row labels (sectors) with the table data
            table_data = df.values
            col_labels = ['Sector'] + df.columns.tolist()  # Add 'Sector' as the first column header

            # Prepend the row_labels to each row of table_data
            # This creates a new list of lists where each sublist starts with the sector name
            full_table_data = [[label] + row.tolist() for label, row in zip(row_labels, table_data)]

            table = ax.table(cellText=full_table_data,
                             colLabels=col_labels,
                             cellLoc='center',  # Alignment of text in cells
                             loc='center')  # Location of the table in the axes (e.g., 'upper left', 'center')

            # Optional: Adjust table properties for better aesthetics
            table.auto_set_font_size(False)
            table.set_fontsize(10)  # Set a specific font size for the table
            table.scale(1.2, 1.2)  # Scale the table (width, height)

            # Optional: Add a title
            ax.set_title('Fort Prices Weekly Percentage Change by Sector', fontsize=14,
                         pad=20)  # pad adds space between title and table

            # 5. Adjust layout to prevent clipping
            plt.tight_layout()

            # 6. Save the figure
            # You can specify the file path and format (e.g., .png, .jpg, .svg, .pdf)
            plt.savefig('../static/images/fort_prices_table.png', bbox_inches='tight',
                        dpi=300)  # dpi for resolution

            plt.show()  # To display the table when run
        else:
            logging.warning("DataFrame is empty after filtering. No Excel files will be generated.")

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
