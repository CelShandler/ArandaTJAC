# importador.py
import os
import sqlite3
import re
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

def extrair_dados_descricao(texto):
    """
    Usa Regex case-insensitive para extrair os metadados textuais 
    embutidos na descrição do chamado.
    """
    if not isinstance(texto, str):
        return "", "", "", "", "", "", "", "", "", ""

    # Dicionário de padrões de busca flexíveis
    padroes = {
        'nome': r'(?:Nome):\s*(.*)',
        'login': r'(?:Login):\s*(.*)',
        'ip': r'(?:IP):\s*(.*)',
        'telefone': r'(?:Telefone):\s*(.*)',
        'ramal': r'(?:Ramal):\s*(.*)',
        'email': r'(?:E-mail|Email):\s*(.*)',
        'localidade': r'(?:Localidade):\s*(.*)',
        'setor': r'(?:Setor):\s*(.*)',
        'patrimonio': r'(?:Patrimônio|Patrimonio):\s*(.*)'
    }

    resultado = {}
    for chave, padrao in padroes.items():
        match = re.search(padrao, texto, re.IGNORECASE)
        resultado[chave] = match.group(1).strip() if match else ""

    # A descrição real do problema costuma ser a primeira linha do bloco de texto
    linhas = [linha.strip() for linha in texto.split('\n') if linha.strip()]
    descricao_problema = linhas[0] if linhas else ""
    
    # Evita que a primeira linha seja salva como a descrição se ela mesma for um rótulo (ex: "Nome: ...")
    if any(descricao_problema.lower().startswith(f"{k}:") for k in padroes.keys()):
        descricao_problema = "Descrição detalhada no corpo do chamado."

    return (
        descricao_problema,
        resultado['nome'],
        resultado['login'],
        resultado['ip'],
        resultado['telefone'],
        resultado['ramal'],
        resultado['email'],
        resultado['localidade'],
        resultado['setor'],
        resultado['patrimonio']
    )

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
        df_a['status'] = 'Ativo'
        dfs.append(df_a)
    if os.path.exists(EXCEL_FECHADOS):
        df_f = pd.read_excel(EXCEL_FECHADOS)
        df_f['status'] = 'Fechado'
        dfs.append(df_f)
        
    if not dfs:
        return
        
    df = pd.concat(dfs, ignore_index=True)
    df.columns = df.columns.str.strip()

    # Mapeamento inicial das colunas base da planilha
    # Cobre variações com e sem acentos, e diferentes formatos de cabeçalho
    colunas_map = {
        # Número do chamado
        'Número': 'numero', 'Numero': 'numero', 'Nº': 'numero', 'N\xfamero': 'numero',
        # Inquilino e Tipo
        'Inquilino': 'inquilino', 'Tipo': 'tipo',
        # Data de Abertura
        'Data Abertura': 'data_abertura', 'Data de Abertura': 'data_abertura',
        # Categoria e Grupo
        'Categoria': 'categoria', 'Grupo': 'grupo',
        # Descrição
        'Descrição': 'descricao', 'Descricao': 'descricao', 'Descri\xe7\xe3o': 'descricao',
        # Data de Resolução — variantes com e sem acento
        'Data Resolução':    'data_resolucao',
        'Data de Resolução': 'data_resolucao',
        'Data Resolucao':    'data_resolucao',
        'Data de Resolucao': 'data_resolucao',
        # Data de Fechamento
        'Data Fechamento':    'data_fechamento',
        'Data de Fechamento': 'data_fechamento',
        # Método Relatado — variantes com e sem acento
        'Método Relatado':  'metodo_relatado',
        'Metodo Relatado':  'metodo_relatado',
        'Método de Relato': 'metodo_relatado',
        # Resolvido Por
        'Resolvido Por': 'resolvido_por', 'Resolvido por': 'resolvido_por',
        # SLA
        'SLA Vencido': 'sla_vencido', 'Sla Vencido': 'sla_vencido',
        # Autor / Usuário
        'Autor': 'autor', 'Usuário': 'usuario', 'Usuario': 'usuario',
        # Prioridade
        'Prioridade': 'prioridade',
        # Cidade e Endereço
        'Cidade Cliente':    'cidade_cliente', 'Cidade_Cliente': 'cidade_cliente', 'Cidade': 'cidade_cliente',
        'Endereço Cliente':  'endereco_cliente', 'Endereco_Cliente': 'endereco_cliente',
        'Endereço':          'endereco_cliente', 'Endereco': 'endereco_cliente',
        # Estado e Comarca
        'Estado': 'estado', 'Comarca': 'comarca',
    }
    df = df.rename(columns=colunas_map)

    # --- ENGENHARIA DE DADOS E REGEX EXTRACTION ---
    # Aplica a função de extração na coluna 'descricao' antiga e gera novas colunas temporárias
    dados_extraidos = df['descricao'].apply(extrair_dados_descricao)
    
    df['desc_problema'] = [d[0] for d in dados_extraidos]
    df['user_nome'] = [d[1] for d in dados_extraidos]
    df['user_login'] = [d[2] for d in dados_extraidos]
    df['user_ip'] = [d[3] for d in dados_extraidos]
    df['user_telefone'] = [d[4] for d in dados_extraidos]
    df['user_ramal'] = [d[5] for d in dados_extraidos]
    df['user_email'] = [d[6] for d in dados_extraidos]
    df['user_localidade'] = [d[7] for d in dados_extraidos]
    df['user_setor'] = [d[8] for d in dados_extraidos]
    df['user_patrimonio'] = [d[9] for d in dados_extraidos]

    # Substitui a descrição poluída pela descrição limpa do problema
    df['descricao'] = df['desc_problema']

    # Regra de negócio: Se comarca estiver vazia ou nula, assume o valor extraído de Localidade
    if 'comarca' in df.columns:
        df['comarca'] = df['comarca'].fillna(df['user_localidade'])
        df.loc[df['comarca'] == '', 'comarca'] = df['user_localidade']
    else:
        df['comarca'] = df['user_localidade']

    # Normalização de Datas
    for col in ['data_abertura', 'data_resolucao', 'data_fechamento']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    # Garantia de colunas aceitas pelo Schema final
    colunas_banco = [
        'inquilino', 'numero', 'tipo', 'data_abertura', 'categoria', 'grupo', 'descricao',
        'data_resolucao', 'data_fechamento', 'metodo_relatado', 'resolvido_por', 'sla_vencido',
        'autor', 'usuario', 'prioridade', 'cidade_cliente', 'endereco_cliente', 'estado', 'comarca',
        'user_nome', 'user_login', 'user_ip', 'user_telefone', 'user_ramal', 'user_email', 'user_setor', 'user_patrimonio',
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
        inquilino TEXT, numero INTEGER, tipo TEXT, data_abertura DATE, categoria TEXT, grupo TEXT,
        descricao TEXT, data_resolucao DATETIME, data_fechamento DATETIME, metodo_relatado TEXT,
        resolvido_por TEXT, sla_vencido INTEGER, autor TEXT, usuario TEXT, prioridade TEXT,
        cidade_cliente TEXT, endereco_cliente TEXT, estado TEXT, comarca TEXT,
        user_nome TEXT, user_login TEXT, user_ip TEXT, user_telefone TEXT, user_ramal TEXT,
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