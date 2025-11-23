import pandas as pd

# 1. Defina o nome do seu arquivo CSV
nome_arquivo_csv = 'seu_arquivo.csv'

# 2. Leia o arquivo CSV para um DataFrame do pandas
# Ajuste o 'sep' (separador) se o seu CSV usar ponto e vírgula (';') ou outro delimitador
try:
    df = pd.read_csv('Futebol Portugues.csv', sep=',')
except FileNotFoundError:
    print(f"Erro: O arquivo '{nome_arquivo_csv}' não foi encontrado.")
    exit()

# 3. Converta o DataFrame em uma string HTML
# index=False impede que o número do índice da linha do pandas apareça na tabela
html_tabela = df.to_html(index=False)