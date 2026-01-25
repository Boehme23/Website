import pandas as pd
import numpy as np
import sqlite3
import os


def calculate_portfolio_stats(selected_assets):
    db_path = os.path.join(os.path.dirname(__file__), './Binance/binance_history.db')
    conn = sqlite3.connect(db_path)
    all_returns = []

    # selected_assets virá como {'BTC': 50, 'ETH': 50}
    for symbol, weight in selected_assets.items():
        # Query filtrando pelo símbolo na tabela consolidada
        query = f"SELECT timestamp, close FROM historico_precos WHERE symbol = '{symbol}' ORDER BY timestamp"
        df = pd.read_sql(query, conn)

        if not df.empty and len(df) > 1:
            df['daily_return'] = df['close'].pct_change()
            # Multiplica o retorno pelo peso relativo
            weighted_series = df.set_index('timestamp')['daily_return'] * (weight / 100)
            all_returns.append(weighted_series)

    conn.close()

    if not all_returns:
        return {"error": "Dados insuficientes para as moedas selecionadas."}

    # Soma os retornos ponderados de todas as moedas selecionadas
    portfolio_series = pd.concat(all_returns, axis=1).sum(axis=1).dropna()

    if portfolio_series.empty:
        return {"error": "Não há datas coincidentes entre as moedas."}

    # Cálculos estatísticos do portfólio consolidado
    return {
        "avg_return": f"{portfolio_series.mean():.4%}",
        "var_99": f"{np.percentile(portfolio_series, 1):.2%}",
        "max_loss": f"{portfolio_series.min():.2%}",
        "max_return": f"{portfolio_series.max():.2%}"
    }