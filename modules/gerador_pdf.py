# modules/gerador_pdf.py
from fpdf import FPDF
import datetime
import pandas as pd
from modules.formatador import formatar_inteiro, formatar_decimal

class RelatorioPDF(FPDF):
    def header(self):
        # Cabeçalho oficial adaptado
        self.set_font("helvetica", "B", 14)
        self.set_text_color(31, 73, 125) # Azul TJAC
        self.cell(0, 8, "TRIBUNAL DE JUSTIÇA DO ESTADO DO ACRE", ln=True, align="C")
        
        self.set_font("helvetica", "", 11)
        self.set_text_color(85, 85, 85) # Cinza escuro
        self.cell(0, 6, "Relatório Analítico de Chamados - BI", ln=True, align="C")
        self.ln(5)
        
        # Linha separadora
        self.set_draw_color(31, 73, 125)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        # Rodapé com numeração de página
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="R")


def normalizar_texto(texto):
    """
    Substitui caracteres Unicode incompatíveis e força a conversão para latin-1,
    garantindo que o gerador de PDF nunca sofra crash por problemas de encoding.
    """
    if texto is None:
        return ""
    
    if not isinstance(texto, str):
        texto = str(texto)
        
    # Dicionário de substituições preventivas (mantém a estética do texto)
    substituicoes = {
        "\u2013": "-",  # en-dash (traço médio) -> hífen comum
        "\u2014": "--", # em-dash (traço longo) -> duplo hífen
        "\u2212": "-",  # minus sign (sinal de menos matemático) -> hífen comum
        "\u201c": '"',  # aspas inteligentes abertas -> aspas padrão
        "\u201d": '"',  # aspas inteligentes fechadas -> aspas padrão
        "\u2018": "'",  # aspa simples inteligente -> apóstrofo
        "\u2019": "'",  # aspa simples inteligente -> apóstrofo
        "\u2022": "*",  # bullet point -> asterisco
        "\u2026": "...",# reticências em caractere único -> três pontos
    }
    
    for original, substituto in substituicoes.items():
        texto = texto.replace(original, substituto)
        
    # Passo final: Codifica em 'latin-1' (padrão da fonte Helvetica) 
    # substituindo qualquer outro caractere desconhecido por "?" para evitar quebras
    texto_seguro = texto.encode("latin-1", errors="replace").decode("latin-1")
    
    return texto_seguro


def gerar_pdf_relatorio(df, filtros_str="Sem filtros", agrupamento=None):
    pdf = RelatorioPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Sessão de Metadados (Data e Filtros)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(0, 0, 0)
    
    data_geracao = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 5, f"Data da Geração: {data_geracao}", ln=True)
    
    if agrupamento:
        pdf.cell(0, 5, normalizar_texto(f"Agrupado por: {', '.join(agrupamento).title()}"), ln=True)
    
    pdf.cell(0, 5, f"Total de Registros: {formatar_inteiro(len(df))}", ln=True)
    pdf.ln(5)
    
    # Desenhando a Tabela
    # 1. Calculando largura das colunas dinamicamente para caber em 190mm (largura útil da página A4)
    colunas = list(df.columns)
    largura_total = 190
    largura_coluna = largura_total / len(colunas)
    
    # 2. Cabeçalho da Tabela
    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(31, 73, 125) # Fundo azul escuro
    pdf.set_text_color(255, 255, 255) # Texto branco
    
    for col in colunas:
        titulo = str(col).title().replace("_", " ")[:20] 
        # Passa o título pelo normalizador
        titulo_limpo = normalizar_texto(titulo)
        pdf.cell(largura_coluna, 8, titulo_limpo, border=1, fill=True, align="C")
    pdf.ln()
    
    # 3. Dados da Tabela
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(0, 0, 0)
    
    fill = False
    for _, linha in df.iterrows():
        # Alternância de cores (Zebra striping)
        if fill:
            pdf.set_fill_color(240, 245, 250) # Azul bem claro
        else:
            pdf.set_fill_color(255, 255, 255) # Branco
            
        for col, dado in zip(colunas, linha):
            # Formata o dado conforme o tipo e nome da coluna para padrão PT-BR
            if isinstance(dado, (pd.Timestamp, datetime.datetime)):
                texto = dado.strftime("%d/%m/%Y %H:%M:%S")
            elif isinstance(dado, float) and not pd.isna(dado):
                texto = formatar_decimal(dado, 1)
            elif isinstance(dado, (int, float)) and not pd.isna(dado):
                if str(col).lower() in ['numero', 'número', 'id']:
                    texto = str(int(dado))
                else:
                    texto = formatar_inteiro(dado)
            else:
                texto = str(dado)
                # Caso seja string com formato de data ISO "YYYY-MM-DD HH:MM:SS", tenta converter e formatar
                if isinstance(dado, str) and len(dado) == 19 and dado[4] == '-' and dado[7] == '-':
                    try:
                        dt_val = pd.to_datetime(dado)
                        texto = dt_val.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        pass

            if len(texto) > 30:
                texto = texto[:27] + "..."
            
            # Passa o dado pelo normalizador de texto antes de renderizar no PDF
            texto_limpo = normalizar_texto(texto)
            pdf.cell(largura_coluna, 6, texto_limpo, border=1, fill=True, align="L")
        
        pdf.ln()
        fill = not fill # Alterna a cor
        
    return bytes(pdf.output())