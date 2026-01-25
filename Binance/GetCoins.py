import pandas as pd
from binance.client import Client
import sqlite3
import time


def configurar_banco():
    # Cria (ou abre) o arquivo de banco de dados
    conn = sqlite3.connect('binance_history.db')
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
            klines = client.get_historical_klines(par, Client.KLINE_INTERVAL_1DAY, "1 Jan, 2023")

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

                # Salva no SQLite (anexa os dados se a tabela já existir)
                df.to_sql('historico_precos', conn, if_exists='append', index=False)

                print(f"[{i + 1}/{len(pares)}] {par} processado com sucesso.")

            # Respeita o limite de peso da API
            time.sleep(0.2)

        except Exception as e:
            print(f"Erro ao processar {par}: {e}")
            continue

    conn.close()
    print("\nProcesso finalizado! Banco 'binance_history.db' pronto.")


baixar_e_salvar_todos()