# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "banco")
DATA_DIR = os.path.join(BASE_DIR, "dados")

DB_PATH = os.path.join(DB_DIR, "chamados.db")
EXCEL_ATIVOS = os.path.join(DATA_DIR, "Chamados_Ativos.xlsx")
EXCEL_FECHADOS = os.path.join(DATA_DIR, "Chamados_Fechados.xlsx")

# Garante a existência dos diretórios
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)