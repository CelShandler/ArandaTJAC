import re
import pandas as pd

# =============================================
# CONFIGURAÇÕES
# =============================================

ARQUIVO_ENTRADA = "dados/TJAC - Base Geral de Chamados.xlsx"
ARQUIVO_SAIDA = "chamados_processado.xlsx"

# Lista de comarcas do TJAC
COMARCAS = [
    "Rio Branco",
    "Porto Acre",
    "Porto Walter",
    "Jordão",
    "Santa Rosa",
    "Marechal Thaumaturgo",
    "Bujari",
    "Sena Madureira",
    "Manoel Urbano",
    "Feijó",
    "Tarauacá",
    "Cruzeiro do Sul",
    "Mâncio Lima",
    "Rodrigues Alves",
    "Senador Guiomard",
    "Capixaba",
    "Acrelândia",
    "Plácido de Castro",
    "Xapuri",
    "Epitaciolândia",
    "Brasiléia",
    "Assis Brasil"
]

# Palavras que indicam início dos campos
MARCADORES = [
    "Categoria:",
    "Login:",
    "Nome:",
    "Telefone:",
    "Ramal:",
    "Email:",
    "Localidade:",
    "Setor:",
    "Patrimônio:",
    "Local de Atuação:",
    "Número de IP / ANYDESK:"
]

# =============================================
# NORMALIZA TEXTO
# =============================================

def normalizar(texto):

    if pd.isna(texto):
        return ""

    texto = str(texto)

    # Remove quebras de linha
    texto = texto.replace("\r", " ")
    texto = texto.replace("\n", " ")

    # Garante espaço antes dos marcadores caso venha tudo colado
    for marcador in MARCADORES:
        texto = re.sub(
            rf'(?<!\s)({re.escape(marcador)})',
            r' \1',
            texto
        )

    # Remove espaços duplicados
    texto = re.sub(r'\s+', ' ', texto)

    return texto.strip()


# =============================================
# EXTRAI UM CAMPO
# =============================================

def extrair(texto, inicio, proximos):

    pos = texto.find(inicio)

    if pos == -1:
        return ""

    pos += len(inicio)

    fim = len(texto)

    for p in proximos:
        x = texto.find(p, pos)

        if x != -1 and x < fim:
            fim = x

    return texto[pos:fim].strip()


# =============================================
# PROCURA A COMARCA
# =============================================

def localizar_comarca(localidade):

    if not localidade:
        return ""

    texto = localidade.lower()

    for comarca in COMARCAS:
        if comarca.lower() in texto:
            return comarca

    return ""


# =============================================
# PROCESSA UMA DESCRIÇÃO
# =============================================

def processar_descricao(descricao):

    descricao = normalizar(descricao)

    resultado = {}

    # -------------------------
    # Descrição limpa
    # -------------------------

    primeira = len(descricao)

    for marcador in MARCADORES:
        p = descricao.find(marcador)
        if p != -1 and p < primeira:
            primeira = p

    resultado["DescricaoNovo"] = descricao[:primeira].strip()

    # -------------------------
    # Campos
    # -------------------------

    resultado["CategoriaExtraida"] = extrair(
        descricao,
        "Categoria:",
        [
            "Login:",
            "Nome:",
            "Telefone:",
            "Ramal:",
            "Email:",
            "Localidade:",
            "Setor:",
            "Patrimônio:",
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Login"] = extrair(
        descricao,
        "Login:",
        [
            "Nome:",
            "Telefone:",
            "Ramal:",
            "Email:",
            "Localidade:",
            "Setor:",
            "Patrimônio:",
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Nome"] = extrair(
        descricao,
        "Nome:",
        [
            "Telefone:",
            "Ramal:",
            "Email:",
            "Localidade:",
            "Setor:",
            "Patrimônio:",
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Telefone"] = extrair(
        descricao,
        "Telefone:",
        [
            "Ramal:",
            "Email:",
            "Localidade:",
            "Setor:",
            "Patrimônio:",
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Ramal"] = extrair(
        descricao,
        "Ramal:",
        [
            "Email:",
            "Localidade:",
            "Setor:",
            "Patrimônio:",
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Email"] = extrair(
        descricao,
        "Email:",
        [
            "Localidade:",
            "Setor:",
            "Patrimônio:",
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    localidade = extrair(
        descricao,
        "Localidade:",
        [
            "Setor:",
            "Patrimônio:",
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Localidade"] = localidade
    resultado["Comarca"] = localizar_comarca(localidade)

    resultado["Setor"] = extrair(
        descricao,
        "Setor:",
        [
            "Patrimônio:",
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Patrimônio"] = extrair(
        descricao,
        "Patrimônio:",
        [
            "Local de Atuação:",
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Local de Atuação"] = extrair(
        descricao,
        "Local de Atuação:",
        [
            "Número de IP / ANYDESK:"
        ]
    )

    resultado["Número de IP / ANYDESK"] = extrair(
        descricao,
        "Número de IP / ANYDESK:",
        []
    )

    return resultado


# =============================================
# LEITURA DO EXCEL
# =============================================

df = pd.read_excel(ARQUIVO_ENTRADA)

# Processa todas as descrições
novos = df["Descricao"].apply(processar_descricao)

# Converte lista de dicionários em DataFrame
novos_df = pd.DataFrame(novos.tolist())

# Junta ao original
df = pd.concat([df, novos_df], axis=1)

# Salva
df.to_excel(ARQUIVO_SAIDA, index=False)

print("Arquivo gerado:", ARQUIVO_SAIDA)