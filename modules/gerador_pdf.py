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
    from fpdf.fonts import FontFace
    
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
    
    # Prepara os dados e cabeçalhos
    colunas = list(df.columns)
    
    # Normalização e formatação prévia dos dados para calcular pesos corretos
    dados_formatados = []
    for _, linha in df.iterrows():
        linha_fmt = []
        for col, dado in zip(colunas, linha):
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
                texto = str(dado) if not pd.isna(dado) else ""
                # Checa ISO date string
                if isinstance(dado, str) and len(dado) == 19 and dado.count('-') >= 2 and dado.count(':') >= 2:
                    try:
                        dt_val = pd.to_datetime(dado)
                        texto = dt_val.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        pass
            
            texto_limpo = normalizar_texto(texto)
            
            # Limite de segurança física da página PDF (Evita crash "row too high")
            # FPDF2 não suporta uma célula maior que a altura de uma página inteira.
            # Limitamos a 20 quebras de linha e 1200 caracteres no total.
            linhas = texto_limpo.split('\n')
            if len(linhas) > 20:
                texto_limpo = '\n'.join(linhas[:20]) + "\n[...]"
                
            if len(texto_limpo) > 1200:
                texto_limpo = texto_limpo[:1197] + "..."
                
            linha_fmt.append(texto_limpo)
        dados_formatados.append(linha_fmt)
        
    # Calcula a largura proporcional (peso) de cada coluna
    pesos = []
    for i, col in enumerate(colunas):
        # Tamanho inicial baseado no cabeçalho
        max_len = len(str(col)) + 2 
        
        # Encontra o maior texto nesta coluna (amostragem simples)
        for linha_fmt in dados_formatados:
            tam = len(linha_fmt[i])
            if tam > max_len:
                max_len = tam
                
        # Limita o peso máximo para não espremer muito outras colunas
        # Descrições enormes (1000 chars) terão peso 120 no max
        if max_len > 120: max_len = 120
        # Tamanho mínimo para não ficar invisível
        if max_len < 10: max_len = 10
            
        pesos.append(max_len)

    pdf.set_font("helvetica", "", 8)
    
    # Estilo do cabeçalho
    headings_style = FontFace(emphasis="B", color=255, fill_color=(31, 73, 125))
    
    # Desenhando a Tabela Dinâmica
    with pdf.table(
        col_widths=pesos,
        text_align="LEFT",
        headings_style=headings_style,
        cell_fill_color=(240, 245, 250),
        cell_fill_mode="ROWS",
    ) as table:
        # Cabeçalho
        linha_cabecalho = table.row()
        for col in colunas:
            titulo = str(col).title().replace("_", " ")
            linha_cabecalho.cell(normalizar_texto(titulo))
            
        # Linhas (dados)
        for linha_fmt in dados_formatados:
            r = table.row()
            for texto in linha_fmt:
                r.cell(texto)
                
    return bytes(pdf.output())