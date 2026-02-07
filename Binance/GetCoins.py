import pandas as pd
from binance.client import Client
import sqlite3
import time


def configurar_banco():
        conn = sqlite3.connect('binance_history.db')
        # Create the table with a UNIQUE constraint on symbol + timestamp
        conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_precos (
            timestamp DATETIME,
            symbol TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            UNIQUE(timestamp, symbol)
        )
        """)
        # 2. Create an index for faster searching/filtering
        conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_time ON historico_precos (symbol, timestamp);")
        return conn

def baixar_e_salvar_todos():
    client = Client()
    conn = configurar_banco()

    # 1. Busca todos os pares que terminam em USDT
    exchange_info = client.get_exchange_info()
    pares = [s['symbol'] for s in exchange_info['symbols']
             if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']

    print(f"Iniciando download de {len(pares)} ativos...")

    for i, par in enumerate(pares):
        try:
            # Baixa dados diários desde 2023 (ajuste a data se necessário)
            klines = client.get_historical_klines(par, Client.KLINE_INTERVAL_1DAY, "1 Jan, 2026")

            if klines:
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'
                ])

                # Tratamento básico
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['symbol'] = par
                cols_numeric = ['open', 'high', 'low', 'close', 'volume']
                df[cols_numeric] = df[cols_numeric].apply(pd.to_numeric)

                # Seleciona colunas úteis
                df = df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
                # 1. Upload to a temporary staging table
                df.to_sql('temp_stats', conn, if_exists='replace', index=False)

                # 2. Move data using INSERT OR IGNORE
                query = """
                                INSERT OR IGNORE INTO historico_precos (timestamp, symbol, open, high, low, close, volume)
                                SELECT timestamp, symbol, open, high, low, close, volume FROM temp_stats;
                                """
                conn.execute(query)
                conn.commit()  # Ensure data is saved

                print(f"[{i + 1}/{len(pares)}] {par} processado.")

            # Respeita o limite de peso da API
            time.sleep(0.2)

        except Exception as e:
            print(f"Erro ao processar {par}: {e}")
            continue

    conn.close()
    print("\nProcesso finalizado! Banco 'binance_history.db' pronto.")


baixar_e_salvar_todos()