import pandas as pd
import os

# 1. Configuração com os nomes específicos que mencionaste
LIGAS = [
    ('ligue-1', 'FR1'),
    ('liga-nos', 'PO1'),
    ('eredivisie', 'NL1'),
    ('premier-league', 'GB1'),
    ('laliga', 'ES1'),  # Aqui usamos laliga/ES1 conforme o teu padrão
    ('bundesliga', 'L1')
]


def merge_csv_files(pattern_template, output_name):
    all_dataframes = []
    print(f"\n--- Processando: {output_name} ---")

    for league_name, league_code in LIGAS:
        # Tenta encontrar o ficheiro usando o código (ES1) ou o nome (laliga / la-liga)
        # O script vai testar as variações que descreveste
        possible_files = [
            pattern_template.format(liga=league_code),
            pattern_template.format(liga=league_name),
            pattern_template.format(liga='la-liga')  # Caso específico que mencionaste
        ]

        file_path = None
        for f in possible_files:
            if os.path.exists(f):
                file_path = f
                break

        if file_path:
            try:
                df = pd.read_csv(file_path)
                df['League'] = league_code

                # Reorganizar colunas
                cols = ['League'] + [c for c in df.columns if c != 'League']
                df = df[cols]

                all_dataframes.append(df)
                print(f"[OK] Carregado: {file_path}")
            except Exception as e:
                print(f"[ERRO] Falha ao ler {file_path}: {e}")
        else:
            print(f"[AVISO] Ficheiro não encontrado para {league_code} (Tentei: {possible_files})")

    if all_dataframes:
        final_df = pd.concat(all_dataframes, ignore_index=True)
        final_df.to_csv(output_name, index=False, encoding='utf-8-sig')
        print(f"SUCESSO! Criado '{output_name}' com {len(final_df)} linhas.")
    else:
        print(f"Nenhum ficheiro encontrado para {output_name}.")


if __name__ == "__main__":
    # 1. Para os ficheiros "Futebol_ES1.csv", etc.
    merge_csv_files("Futebol_{liga}.csv", "All_Leagues_Combined.csv")

    # 2. Para os ficheiros "Schedule_laliga.csv", etc.
    merge_csv_files("Schedule_{liga}.csv", "All_Schedule_Combined.csv")

    # 3. Para os ficheiros "Proximos jogos da la-liga.csv", etc.
    merge_csv_files("Proximos jogos da {liga}.csv", "All_Proximos_Jogos.csv")