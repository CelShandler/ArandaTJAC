FROM python:3.13-slim

# Evita geração de bytecode .pyc e força stdout/stderr sem buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copia arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código para a imagem
COPY . .

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Healthcheck da aplicação Streamlit usando biblioteca nativa do Python (sem necessidade de apt-get/curl)
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Executa o Streamlit apontando para 0.0.0.0
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
