import pandas as pd
import os
from thefuzz import process, fuzz


def buscar_nome_similar(nome, lista_referencia, threshold=80):
    """
    Se encontrar um nome muito parecido na base antiga, retorna o nome antigo
    para manter a consistência e permitir o drop_duplicates.
    """
    if not lista_referencia or pd.isna(nome):
        return nome

    # Busca o melhor match na lista de nomes já existentes
    match, score = process.extractOne(nome, lista_referencia, scorer=fuzz.token_sort_ratio)

    if score >= threshold:
        return match
    return nome


def atualizar_base_combinada(arquivo_liga):
    caminho_combinado = 'All_Schedule_Combined.csv'

    if not os.path.exists(arquivo_liga):
        print(f"Arquivo {arquivo_liga} não encontrado.")
        return

    df_novo = pd.read_csv(arquivo_liga)

    if os.path.exists(caminho_combinado):
        df_base = pd.read_csv(caminho_combinado)

        # --- LÓGICA FUZZY ---
        # Criamos uma lista de nomes únicos de times que já estão na base
        times_na_base = set(df_base['Home'].tolist() + df_base['Away'].tolist())

        print("Verificando consistência de nomes com TheFuzz...")
        # Ajusta os nomes no DF novo para baterem com o que já existe
        df_novo['Home'] = df_novo['Home'].apply(lambda x: buscar_nome_similar(x, times_na_base))
        df_novo['Away'] = df_novo['Away'].apply(lambda x: buscar_nome_similar(x, times_na_base))
    else:
        df_base = pd.DataFrame(columns=['Round', 'Home', 'Away', 'League'])

    # 3. Concatenar e remover duplicatas
    df_final = pd.concat([df_base, df_novo], ignore_index=True)

    # Agora o drop_duplicates funcionará mesmo se o nome era levemente diferente
    df_final = df_final.drop_duplicates(
        subset=['Round', 'Home', 'Away', 'League'],
        keep='last'
    )

    df_final.to_csv(caminho_combinado, index=False, encoding='utf-8')
    print(f"✅ Base combinada atualizada (Fuzzy Match aplicado)")


if __name__ == '__main__':
    arquivos_para_processar = ['All_Proximos_Jogos.csv']
    for arquivo in arquivos_para_processar:
        atualizar_base_combinada(arquivo)