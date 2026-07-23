# importador.py
import os
import sqlite3
import pandas as pd
from config import DB_PATH, EXCEL_ATIVOS, EXCEL_FECHADOS

def obter_mtime_excel():
    mtimes = []
    if os.path.exists(EXCEL_ATIVOS):
        mtimes.append(os.path.getmtime(EXCEL_ATIVOS))
    if os.path.exists(EXCEL_FECHADOS):
        mtimes.append(os.path.getmtime(EXCEL_FECHADOS))
    
    if not mtimes:
        return None
    return max(mtimes)

def verificar_e_atualizar():
    mtime_atual = obter_mtime_excel()
    if mtime_atual is None:
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS controle_importacao (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)
    conn.commit()

    cursor.execute("SELECT valor FROM controle_importacao WHERE chave = 'ultimo_mtime'")
    row = cursor.fetchone()
    ultimo_mtime = float(row[0]) if row else None

    if ultimo_mtime is None or mtime_atual > ultimo_mtime:
        importar_dados(conn, mtime_atual)
        conn.close()
        return True

    conn.close()
    return False

def importar_dados(conn, mtime):
    dfs = []
    if os.path.exists(EXCEL_ATIVOS):
        df_a = pd.read_excel(EXCEL_ATIVOS)
        df_a['status_arquivo'] = 'Ativo'
        dfs.append(df_a)
    if os.path.exists(EXCEL_FECHADOS):
        df_f = pd.read_excel(EXCEL_FECHADOS)
        df_f['status_arquivo'] = 'Fechado'
        dfs.append(df_f)
        
    if not dfs:
        return
        
    df = pd.concat(dfs, ignore_index=True)
    df.columns = df.columns.str.strip()

    # Mapeamento inicial das colunas base da planilha
    colunas_map = {
        'Número': 'numero', 'Numero': 'numero', 'Nº': 'numero', 'N\xfamero': 'numero',
        'Tipo': 'tipo',
        'Data de Abertura': 'data_abertura', 'Data Abertura': 'data_abertura',
        'Categoria': 'categoria', 'Grupo': 'grupo',
        'Descricao': 'descricao', 'Descrição': 'descricao', 'Descri\xe7\xe3o': 'descricao', 'Descricao_Detalhada': 'descricao_detalhada',
        'Data de Resolucao': 'data_resolucao', 'Data Resolução': 'data_resolucao', 'Data de Resolução': 'data_resolucao', 'Data Resolucao': 'data_resolucao',
        'Data de Fechamento': 'data_fechamento', 'Data Fechamento': 'data_fechamento',
        'Metodo Relatado': 'metodo_relatado', 'Método Relatado': 'metodo_relatado', 'Método de Relato': 'metodo_relatado',
        'Resolvido Por': 'resolvido_por', 'Resolvido por': 'resolvido_por',
        'SLA Vencido': 'sla_vencido', 'Sla Vencido': 'sla_vencido',
        'Autor': 'autor', 'Usuário': 'usuario', 'Usuario': 'usuario',
        'Prioridade': 'prioridade',
        'Endereco_Cliente': 'endereco_cliente', 'Endereço Cliente': 'endereco_cliente', 'Endereço': 'endereco_cliente', 'Endereco': 'endereco_cliente',
        'Comarca': 'comarca',
        'Login': 'user_login',
        'Nome': 'user_nome',
        'Telefone': 'user_telefone',
        'Email': 'user_email', 'E-mail': 'user_email',
        'Localidade': 'user_localidade', 'Local de Atuação': 'user_localidade', 'Local de Atuacao': 'user_localidade',
        'Setor': 'user_setor',
        'Patrimônio': 'user_patrimonio', 'Patrimonio': 'user_patrimonio',
        'Número de IP / ANYDESK': 'user_ip', 'Numero de IP / ANYDESK': 'user_ip', 'IP': 'user_ip',
        'Status': 'status'
    }
    df = df.rename(columns=colunas_map)

    # Se status não existir no excel, pega de 'status_arquivo'
    if 'status' not in df.columns:
        df['status'] = df['status_arquivo']

    # Regra de negócio: Se comarca estiver vazia ou nula, assume o valor extraído de Localidade
    if 'comarca' in df.columns and 'user_localidade' in df.columns:
        df['comarca'] = df['comarca'].fillna(df['user_localidade'])
        df.loc[df['comarca'] == '', 'comarca'] = df['user_localidade']
    elif 'user_localidade' in df.columns:
        df['comarca'] = df['user_localidade']
    elif 'comarca' not in df.columns:
        df['comarca'] = None

    # Normalização de Datas
    for col in ['data_abertura', 'data_resolucao', 'data_fechamento']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    # Garantia de colunas aceitas pelo Schema final
    colunas_banco = [
        'numero', 'tipo', 'data_abertura', 'categoria', 'grupo', 'descricao',
        'data_resolucao', 'data_fechamento', 'metodo_relatado', 'resolvido_por', 'sla_vencido',
        'autor', 'usuario', 'prioridade', 'endereco_cliente', 'comarca',
        'user_nome', 'user_login', 'user_ip', 'user_telefone', 'user_email', 'user_setor', 'user_patrimonio',
        'status'
    ]
    colunas_para_inserir = [col for col in colunas_banco if col in df.columns]
    df = df[colunas_para_inserir]

    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS chamados")
    cursor.execute("DROP TABLE IF EXISTS chamados_fts")

    # Schema Atualizado com as Novas Colunas Estruturadas
    cursor.execute("""
    CREATE TABLE chamados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER, tipo TEXT, data_abertura DATE, categoria TEXT, grupo TEXT,
        descricao TEXT, data_resolucao DATETIME, data_fechamento DATETIME, metodo_relatado TEXT,
        resolvido_por TEXT, sla_vencido INTEGER, autor TEXT, usuario TEXT, prioridade TEXT,
        endereco_cliente TEXT, comarca TEXT,
        user_nome TEXT, user_login TEXT, user_ip TEXT, user_telefone TEXT,
        user_email TEXT, user_setor TEXT, user_patrimonio TEXT, status TEXT
    );
    """)

    df.to_sql('chamados', conn, if_exists='append', index=False)

    # Criação do FTS5 Virtual incluindo os novos campos para buscas instantâneas na Aba 3
    try:
        cursor.execute("""
            CREATE VIRTUAL TABLE chamados_fts USING fts5(
                id UNINDEXED, numero, autor, descricao, resolvido_por, comarca,
                user_nome, user_login, user_ip, user_patrimonio
            )
        """)
        cursor.execute("""
            INSERT INTO chamados_fts(id, numero, autor, descricao, resolvido_por, comarca, user_nome, user_login, user_ip, user_patrimonio)
            SELECT id, numero, autor, descricao, resolvido_por, comarca, user_nome, user_login, user_ip, user_patrimonio FROM chamados
        """)
    except sqlite3.OperationalError:
        pass

    cursor.execute("INSERT OR REPLACE INTO controle_importacao (chave, valor) VALUES ('ultimo_mtime', ?)", (str(mtime),))
    conn.commit()