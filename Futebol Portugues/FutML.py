import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report


data = pd.read_csv('Futebol Portugues.csv')
confrontos_futuros = pd.read_csv('Futebol Portugues_Jogos.csv')
confrontos = pd.read_csv('../resultados.csv')

