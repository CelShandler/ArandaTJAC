# modules/formatador.py
import pandas as pd
import datetime

def formatar_inteiro(valor):
    """
    Formata um número inteiro no padrão PT-BR (ex: 50946 -> 50.946).
    Retorna string vazia ou string formatada.
    """
    if pd.isna(valor) or valor is None:
        return ""
    try:
        val_int = int(valor)
        return f"{val_int:,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(valor)

def formatar_decimal(valor, precisao=1):
    """
    Formata um número decimal no padrão PT-BR (ex: 97.5 -> 97,5).
    Usa ponto para milhares e vírgula para decimais.
    """
    if pd.isna(valor) or valor is None:
        return ""
    try:
        val_float = float(valor)
        formatted = f"{val_float:,.{precisao}f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(valor)

def formatar_data(data):
    """
    Formata uma data para o padrão PT-BR (dd/mm/aaaa).
    Aceita strings de data, objetos datetime ou Timestamps do Pandas.
    """
    if pd.isna(data) or data is None:
        return ""
    try:
        if isinstance(data, str):
            dt = pd.to_datetime(data)
        else:
            dt = data
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(data)

def formatar_data_hora(data):
    """
    Formata data e hora para o padrão PT-BR (dd/mm/aaaa hh:mm:ss).
    """
    if pd.isna(data) or data is None:
        return ""
    try:
        if isinstance(data, str):
            dt = pd.to_datetime(data)
        else:
            dt = data
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(data)

def formatar_moeda(valor):
    """
    Formata um valor como moeda no formato brasileiro (R$ 1.234,56).
    """
    if pd.isna(valor) or valor is None:
        return ""
    try:
        val_float = float(valor)
        formatted = f"{val_float:,.2f}"
        val_str = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {val_str}"
    except (ValueError, TypeError):
        return str(valor)
