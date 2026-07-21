# app.py
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
from config import DB_PATH
import importador
from modules.gerador_pdf import gerar_pdf_relatorio
from modules.formatador import formatar_inteiro, formatar_decimal, formatar_data_hora

# ============================================================
# Configuração da Página
# ============================================================
st.set_page_config(
    page_title="TJAC - Chamados BI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# Injeção do CSS Premium
# ============================================================
_css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
with open(_css_path, encoding="utf-8") as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ============================================================
# Configuração das colunas de data para os dataframes
# ============================================================
DF_COL_CONFIG = {
    "data_abertura":  st.column_config.DatetimeColumn("Data Abertura",  format="DD/MM/YYYY HH:mm:ss"),
    "data_resolucao": st.column_config.DatetimeColumn("Data Resolução",  format="DD/MM/YYYY HH:mm:ss"),
    "data_fechamento":st.column_config.DatetimeColumn("Data Fechamento", format="DD/MM/YYYY HH:mm:ss"),
    "numero":         st.column_config.NumberColumn("Número", format="%d"),
    "Quantidade Total": st.column_config.NumberColumn("Quantidade Total", format="%d"),
}

# ============================================================
# Função para aplicar tema padronizado a gráficos Plotly
# ============================================================
def aplicar_tema_grafico(fig, height=None):
    """Aplica tema escuro responsivo e harmonizado a figuras Plotly."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#8fa7c4", size=11),
        title_font=dict(family="Outfit, sans-serif", color="#c8ddf5", size=14, weight="bold" if hasattr(dict, "weight") else None),
        margin=dict(l=8, r=8, t=42, b=8),
        legend=dict(
            bgcolor="rgba(255,255,255,0.04)",
            bordercolor="rgba(255,255,255,0.08)",
            borderwidth=1,
            font=dict(color="#8fa7c4")
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            linecolor="rgba(255,255,255,0.1)",
            tickcolor="rgba(255,255,255,0.1)",
            tickfont=dict(color="#8fa7c4"),
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            linecolor="rgba(255,255,255,0.1)",
            tickcolor="rgba(255,255,255,0.1)",
            tickfont=dict(color="#8fa7c4"),
        ),
        coloraxis_colorbar=dict(
            tickfont=dict(color="#8fa7c4"),
            title_font=dict(color="#8fa7c4"),
        ),
    )
    if height:
        fig.update_layout(height=height)
    return fig

# ============================================================
# 1. Sincronização da Base de Dados
# ============================================================
if 'atualizado' not in st.session_state:
    with st.spinner("Sincronizando base de dados..."):
        st.session_state['atualizado'] = importador.verificar_e_atualizar()

if st.session_state['atualizado']:
    st.toast("Banco de dados atualizado com a última versão do Excel! 🚀")

# Função de leitura rápida (com cache inteligente que invalida se o banco mudar)
import os
@st.cache_data
def carregar_dados_do_banco(mtime):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM chamados", conn)
    conn.close()
    df['data_abertura']   = pd.to_datetime(df['data_abertura'])
    df['data_resolucao']  = pd.to_datetime(df['data_resolucao'])
    df['data_fechamento'] = pd.to_datetime(df['data_fechamento'])
    return df

db_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else 0
df = carregar_dados_do_banco(db_mtime)

# ============================================================
# 2. Header Principal
# ============================================================
total_geral = len(df)
st.markdown(f"""
<div class="main-header">
    <h1>⚖️ TJAC — Central de Chamados BI</h1>
    <p>Tribunal de Justiça do Estado do Acre · Painel de Inteligência Operacional</p>
    <span class="badge">📦 {formatar_inteiro(total_geral)} chamados na base</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 3. Sidebar — Filtros Globais
# ============================================================
st.sidebar.title("🔧 Filtros Globais")

min_dt = df['data_abertura'].min().date() if not df.empty else None
max_dt = df['data_abertura'].max().date() if not df.empty else None
if min_dt and max_dt:
    periodo = st.sidebar.date_input(
        "Período de Abertura", [min_dt, max_dt], format="DD/MM/YYYY"
    )
else:
    periodo = None

def filtro_multiselect(label, coluna):
    opcoes = sorted(df[coluna].dropna().unique().tolist())
    return st.sidebar.multiselect(label, opcoes)

grupo_sel      = filtro_multiselect("Grupo",        "grupo")
categoria_sel  = filtro_multiselect("Categoria",    "categoria")
comarca_sel    = filtro_multiselect("Comarca",      "comarca")
tipo_sel       = filtro_multiselect("Tipo",         "tipo")
status_sel     = filtro_multiselect("Status",       "status")
prioridade_sel = filtro_multiselect("Prioridade",   "prioridade")
estado_sel     = filtro_multiselect("Estado",       "estado")
autor_sel      = filtro_multiselect("Autor",        "autor")
resolvido_sel  = filtro_multiselect("Resolvido por","resolvido_por")
cidade_sel     = filtro_multiselect("Cidade",       "cidade_cliente")

# Aplicação dos Filtros
df_filtrado = df.copy()
if periodo and len(periodo) == 2:
    df_filtrado = df_filtrado[
        (df_filtrado['data_abertura'].dt.date >= periodo[0]) &
        (df_filtrado['data_abertura'].dt.date <= periodo[1])
    ]
if grupo_sel:      df_filtrado = df_filtrado[df_filtrado['grupo'].isin(grupo_sel)]
if categoria_sel:  df_filtrado = df_filtrado[df_filtrado['categoria'].isin(categoria_sel)]
if comarca_sel:    df_filtrado = df_filtrado[df_filtrado['comarca'].isin(comarca_sel)]
if tipo_sel:       df_filtrado = df_filtrado[df_filtrado['tipo'].isin(tipo_sel)]
if status_sel:     df_filtrado = df_filtrado[df_filtrado['status'].isin(status_sel)]
if prioridade_sel: df_filtrado = df_filtrado[df_filtrado['prioridade'].isin(prioridade_sel)]
if estado_sel:     df_filtrado = df_filtrado[df_filtrado['estado'].isin(estado_sel)]
if autor_sel:      df_filtrado = df_filtrado[df_filtrado['autor'].isin(autor_sel)]
if resolvido_sel:  df_filtrado = df_filtrado[df_filtrado['resolvido_por'].isin(resolvido_sel)]
if cidade_sel:     df_filtrado = df_filtrado[df_filtrado['cidade_cliente'].isin(cidade_sel)]

# Info de filtros aplicados na sidebar
qtd_filtrado = len(df_filtrado)
st.sidebar.markdown("---")
st.sidebar.markdown(f"**📊 Chamados filtrados:** `{formatar_inteiro(qtd_filtrado)}`")

# ============================================================
# 4. Abas do Painel
# ============================================================
tab_dash, tab_rel, tab_busca, tab_ind, tab_ana = st.tabs([
    "📊 Dashboard",
    "🗂️ Relatórios",
    "🔍 Pesquisar Chamado",
    "📈 Indicadores",
    "💡 Análises"
])

# ============================================================
# ─── ABA 1: DASHBOARD ───────────────────────────────────────
# ============================================================
with tab_dash:
    # ── KPIs ──
    total_chamados = len(df_filtrado)
    resolvidos  = len(df_filtrado[df_filtrado['data_resolucao'].notna()])
    vencidos    = len(df_filtrado[df_filtrado['sla_vencido'] == 1])
    cumpridos   = total_chamados - vencidos

    sla_cumprido_pct = (cumpridos / total_chamados * 100) if total_chamados > 0 else 100
    sla_vencido_pct  = (vencidos  / total_chamados * 100) if total_chamados > 0 else 0

    df_res_tmp = df_filtrado[
        df_filtrado['data_resolucao'].notna() & df_filtrado['data_abertura'].notna()
    ].copy()
    if not df_res_tmp.empty:
        df_res_tmp['tempo_res'] = (
            df_res_tmp['data_resolucao'] - df_res_tmp['data_abertura']
        ).dt.total_seconds() / 3600
        tempo_medio = f"{formatar_decimal(df_res_tmp['tempo_res'].mean(), 1)}h"
    else:
        tempo_medio = "N/A"

    # KPIs responsivos via HTML
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card blue">
            <span class="kpi-icon">📋</span>
            <div class="kpi-label">Total de Chamados</div>
            <div class="kpi-value">{formatar_inteiro(total_chamados)}</div>
            <div class="kpi-sub">No período selecionado</div>
        </div>
        <div class="kpi-card green">
            <span class="kpi-icon">✅</span>
            <div class="kpi-label">Resolvidos</div>
            <div class="kpi-value">{formatar_inteiro(resolvidos)}</div>
            <div class="kpi-sub">Com data de resolução</div>
        </div>
        <div class="kpi-card teal">
            <span class="kpi-icon">🎯</span>
            <div class="kpi-label">SLA Cumprido</div>
            <div class="kpi-value">{formatar_decimal(sla_cumprido_pct, 1)}%</div>
            <div class="kpi-sub">{formatar_inteiro(cumpridos)} chamados no prazo</div>
        </div>
        <div class="kpi-card orange">
            <span class="kpi-icon">⚠️</span>
            <div class="kpi-label">SLA Vencido</div>
            <div class="kpi-value">{formatar_decimal(sla_vencido_pct, 1)}%</div>
            <div class="kpi-sub">{formatar_inteiro(vencidos)} chamados em atraso</div>
        </div>
        <div class="kpi-card violet">
            <span class="kpi-icon">⏱️</span>
            <div class="kpi-label">Tempo Médio</div>
            <div class="kpi-value">{tempo_medio}</div>
            <div class="kpi-sub">Horas até resolução</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Gráficos ──
    g_col1, g_col2 = st.columns(2, gap="medium")

    with g_col1:
        df_mes = df_filtrado.groupby(
            df_filtrado['data_abertura'].dt.to_period("M")
        ).size().reset_index(name='Qtd')
        df_mes['data_abertura'] = df_mes['data_abertura'].dt.strftime('%m/%Y')
        fig_mes = px.line(
            df_mes, x='data_abertura', y='Qtd',
            title="📈 Evolução Mensal de Abertura", markers=True,
            color_discrete_sequence=["#60a5fa"]
        )
        fig_mes.update_traces(
            line=dict(width=2.5),
            marker=dict(size=6, color="#3b82f6", line=dict(width=1.5, color="#93c5fd"))
        )
        st.plotly_chart(aplicar_tema_grafico(fig_mes, height=300), use_container_width=True, key="1")

        df_cat = df_filtrado['categoria'].value_counts().reset_index(name='Qtd').head(15)
        fig_cat = px.bar(
            df_cat, x='categoria', y='Qtd',
            title="🏷️ Top 15 Categorias de Chamados",
            color='Qtd', color_continuous_scale="Blues"
        )
        fig_cat.update_xaxes(tickangle=-35)
        st.plotly_chart(aplicar_tema_grafico(fig_cat, height=320), use_container_width=True, key="2")

    with g_col2:
        fig_sla = px.pie(
            names=['Cumprido', 'Vencido'], values=[cumpridos, vencidos],
            title="🎯 Status de SLA", hole=0.55,
            color_discrete_sequence=["#10b981", "#f59e0b"]
        )
        fig_sla.update_traces(textposition='outside', textinfo='percent+label',
                              marker=dict(line=dict(color="rgba(0,0,0,0)", width=0)))
        st.plotly_chart(aplicar_tema_grafico(fig_sla, height=300), use_container_width=True, key="3")

        df_comarca = df_filtrado['comarca'].value_counts().reset_index(name='Qtd').head(10)
        fig_comarca = px.bar(
            df_comarca, x='Qtd', y='comarca', orientation='h',
            title="📍 Top 10 Comarcas",
            color='Qtd', color_continuous_scale="Teal"
        )
        fig_comarca.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(aplicar_tema_grafico(fig_comarca, height=320), use_container_width=True, key="4")

# ============================================================
# ─── ABA 2: RELATÓRIOS ──────────────────────────────────────
# ============================================================
with tab_rel:
    st.markdown('<p class="section-title">🗂️ Gerador de Relatórios Customizados</p>', unsafe_allow_html=True)

    col_config, col_preview = st.columns([1, 3], gap="large")

    with col_config:
        st.markdown("**1. Escolha as Colunas**")
        colunas_disponiveis = {
            "Número": "numero", "Data Abertura": "data_abertura", "Grupo": "grupo",
            "Categoria": "categoria", "Comarca": "comarca", "Autor": "autor",
            "Resolvido Por": "resolvido_por", "Estado": "estado", "SLA Vencido": "sla_vencido",
            "Status": "status", "IP do Usuário": "user_ip", "Login": "user_login", 
            "Nome Completo": "user_nome", "Patrimônio": "user_patrimonio", 
            "Setor": "user_setor", "Ramal": "user_ramal"
        }
        selecionadas_nomes = []
        for nome in colunas_disponiveis.keys():
            if st.checkbox(nome, value=nome in ["Número", "Data Abertura", "Grupo", "Categoria", "Comarca"]):
                selecionadas_nomes.append(nome)
        colunas_db = [colunas_disponiveis[n] for n in selecionadas_nomes]

        st.markdown("---")
        st.markdown("**2. Agrupamento Opcional**")
        agrupamento = st.multiselect(
            "Agrupar por:",
            ["grupo", "comarca", "resolvido_por", "categoria", "estado"]
        )
        st.markdown("---")
        ordenacao = st.radio("Ordenação", ["Crescente", "Decrescente"])

    with col_preview:
        if df_filtrado.empty:
            st.warning("Nenhum dado encontrado com os filtros globais aplicados.")
        else:
            if agrupamento:
                df_rel = df_filtrado.groupby(agrupamento).size().reset_index(name="Quantidade Total")
                df_rel = df_rel.sort_values(by="Quantidade Total", ascending=(ordenacao == "Crescente"))
            else:
                df_rel = df_filtrado[colunas_db].copy()
                if "data_abertura" in colunas_db:
                    df_rel = df_rel.sort_values(by="data_abertura", ascending=(ordenacao == "Crescente"))

            st.dataframe(df_rel, use_container_width=True, hide_index=True, column_config=DF_COL_CONFIG)

            st.markdown("### 📥 Exportar Relatório Filtrado")
            exp_col1, exp_col2, exp_col3 = st.columns(3, gap="small")

            # 1. CSV (PT-BR)
            df_csv = df_rel.copy()
            for col in df_csv.columns:
                if pd.api.types.is_datetime64_any_dtype(df_csv[col]):
                    df_csv[col] = df_csv[col].dt.strftime('%d/%m/%Y %H:%M:%S')
                elif pd.api.types.is_float_dtype(df_csv[col]):
                    df_csv[col] = df_csv[col].apply(
                        lambda x: str(x).replace('.', ',') if not pd.isna(x) else ""
                    )
            csv_data = df_csv.to_csv(index=False, sep=";", encoding="utf-8-sig").encode('utf-8-sig')
            exp_col1.download_button(
                label="📄 Baixar CSV",
                data=csv_data,
                file_name="relatorio_tj.csv",
                mime="text/csv"
            )

            # 2. Excel
            import io
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_rel.to_excel(writer, index=False, sheet_name='Chamados Filtrados')
            exp_col2.download_button(
                label="📊 Baixar Excel",
                data=output_excel.getvalue(),
                file_name="relatorio_tj.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # 3. PDF
            with st.spinner("Preparando motor de PDF..."):
                pdf_bytes = gerar_pdf_relatorio(df=df_rel, agrupamento=agrupamento)
                exp_col3.download_button(
                    label="📕 Baixar PDF Oficial",
                    data=pdf_bytes,
                    file_name="relatorio_oficial_tj.pdf",
                    mime="application/pdf"
                )

# ============================================================
# ─── ABA 3: PESQUISA ────────────────────────────────────────
# ============================================================
with tab_busca:
    st.markdown('<p class="section-title">🔍 Pesquisa Textual Inteligente</p>', unsafe_allow_html=True)
    termo_pesquisa = st.text_input(
        "Digite o termo (Número, Autor, Descrição, IP, AnyDesk, CPF, etc.):", ""
    )

    if termo_pesquisa:
        conn = sqlite3.connect(DB_PATH)
        try:
            query = """
                SELECT c.* FROM chamados c
                JOIN chamados_fts f ON c.id = f.id
                WHERE chamados_fts MATCH ?
            """
            df_busca = pd.read_sql_query(query, conn, params=(f"*{termo_pesquisa}*",))
        except Exception:
            query = """
                SELECT * FROM chamados
                WHERE numero LIKE ? OR autor LIKE ? OR descricao LIKE ? OR resolvido_por LIKE ?
                OR comarca LIKE ? OR user_ip LIKE ? OR user_patrimonio LIKE ? OR user_login LIKE ?
            """
            param = f"%{termo_pesquisa}%"
            df_busca = pd.read_sql_query(query, conn, params=(param,)*8)
        conn.close()

        if not df_busca.empty:
            for col in ['data_abertura', 'data_resolucao', 'data_fechamento']:
                if col in df_busca.columns:
                    df_busca[col] = pd.to_datetime(df_busca[col], errors='coerce')
            st.write(f"Foram encontrados **{formatar_inteiro(len(df_busca))}** chamados para '{termo_pesquisa}':")
            st.dataframe(df_busca, use_container_width=True, hide_index=True, column_config=DF_COL_CONFIG)
        else:
            st.info("Nenhum registro encontrado para essa busca.")

# ============================================================
# ─── ABA 4: INDICADORES ─────────────────────────────────────
# ============================================================
with tab_ind:
    st.markdown('<p class="section-title">📈 Métricas de Desempenho e Produtividade</p>', unsafe_allow_html=True)

    if df_filtrado.empty:
        st.warning("Sem dados disponíveis para calcular os indicadores com os filtros atuais.")
    else:
        df_tempo = df_filtrado.copy()
        df_tempo['data_abertura']   = pd.to_datetime(df_tempo['data_abertura'],   errors='coerce')
        df_tempo['data_resolucao']  = pd.to_datetime(df_tempo['data_resolucao'],  errors='coerce')
        df_tempo['data_fechamento'] = pd.to_datetime(df_tempo['data_fechamento'], errors='coerce')

        status_resolvido = (
            df_tempo['estado'].astype(str).str.upper().str.strip()
            .isin(['RESOLVED', 'RESOLVIDO', 'FECHADO', 'CLOSED'])
        )
        tem_data_fim = df_tempo['data_resolucao'].notna() | df_tempo['data_fechamento'].notna()
        df_resolvidos_geral = df_tempo[status_resolvido | tem_data_fim].copy()
        df_resolvidos_geral['data_fim_efetiva'] = (
            df_resolvidos_geral['data_resolucao'].fillna(df_resolvidos_geral['data_fechamento'])
        )

        df_com_tempo = df_resolvidos_geral[
            df_resolvidos_geral['data_abertura'].notna() &
            df_resolvidos_geral['data_fim_efetiva'].notna()
        ].copy()
        df_com_tempo['tempo_horas'] = (
            df_com_tempo['data_fim_efetiva'] - df_com_tempo['data_abertura']
        ).dt.total_seconds() / 3600
        df_com_tempo = df_com_tempo[df_com_tempo['tempo_horas'] >= 0]

        sub_tab_tempo, sub_tab_vol, sub_tab_rankings = st.tabs([
            "⏱️ Tempos Médios", "📅 Evolução Temporal", "🏆 Rankings (Top 20)"
        ])

        # Sub-aba: Tempos Médios
        with sub_tab_tempo:
            st.markdown("### ⏱️ Tempo Médio de Resolução (Horas)")
            if df_com_tempo.empty:
                st.info("💡 Chamados marcados como resolvidos, mas colunas de data ausentes ou inconsistentes.")
            else:
                col_t1, col_t2, col_t3 = st.columns(3, gap="small")

                with col_t1:
                    st.markdown('<p class="section-title">Por Comarca</p>', unsafe_allow_html=True)
                    tempo_comarca = (
                        df_com_tempo.groupby('comarca')['tempo_horas'].mean()
                        .reset_index().sort_values(by='tempo_horas', ascending=False)
                    )
                    fig_t_comarca = px.bar(
                        tempo_comarca, x='tempo_horas', y='comarca', orientation='h',
                        labels={'tempo_horas': 'Horas Médias', 'comarca': 'Comarca'},
                        color='tempo_horas', color_continuous_scale='Reds'
                    )
                    st.plotly_chart(aplicar_tema_grafico(fig_t_comarca), use_container_width=True, key="5")

                with col_t2:
                    st.markdown('<p class="section-title">Por Técnico</p>', unsafe_allow_html=True)
                    tempo_tecnico = (
                        df_com_tempo.groupby('resolvido_por')['tempo_horas'].mean()
                        .reset_index().sort_values(by='tempo_horas', ascending=False).head(15)
                    )
                    fig_t_tec = px.bar(
                        tempo_tecnico, x='tempo_horas', y='resolvido_por', orientation='h',
                        labels={'tempo_horas': 'Horas Médias', 'resolvido_por': 'Técnico'},
                        color='tempo_horas', color_continuous_scale='Oranges'
                    )
                    st.plotly_chart(aplicar_tema_grafico(fig_t_tec), use_container_width=True, key="6")

                with col_t3:
                    st.markdown('<p class="section-title">Por Categoria</p>', unsafe_allow_html=True)
                    tempo_cat = (
                        df_com_tempo.groupby('categoria')['tempo_horas'].mean()
                        .reset_index().sort_values(by='tempo_horas', ascending=False).head(15)
                    )
                    fig_t_cat = px.bar(
                        tempo_cat, x='tempo_horas', y='categoria', orientation='h',
                        labels={'tempo_horas': 'Horas Médias', 'categoria': 'Categoria'},
                        color='tempo_horas', color_continuous_scale='Purples'
                    )
                    st.plotly_chart(aplicar_tema_grafico(fig_t_cat), use_container_width=True, key="7")

        # Sub-aba: Evolução Temporal
        with sub_tab_vol:
            st.markdown("### 📅 Tendência de Aberturas")
            col_v1, col_v2, col_v3 = st.columns(3, gap="small")

            with col_v1:
                st.markdown('<p class="section-title">Chamados por Dia</p>', unsafe_allow_html=True)
                vol_dia = df_tempo.groupby(df_tempo['data_abertura'].dt.date).size().reset_index(name='Qtd')
                fig_v_dia = px.line(vol_dia, x='data_abertura', y='Qtd', markers=True,
                                    color_discrete_sequence=["#60a5fa"])
                fig_v_dia.update_xaxes(tickformat="%d/%m/%Y")
                st.plotly_chart(aplicar_tema_grafico(fig_v_dia), use_container_width=True, key="8")

            with col_v2:
                st.markdown('<p class="section-title">Chamados por Semana</p>', unsafe_allow_html=True)
                df_tempo['semana'] = df_tempo['data_abertura'].dt.to_period('W').dt.to_timestamp()
                vol_semana = df_tempo.groupby('semana').size().reset_index(name='Qtd')
                fig_v_semana = px.line(vol_semana, x='semana', y='Qtd', markers=True,
                                       color_discrete_sequence=["#34d399"])
                fig_v_semana.update_xaxes(tickformat="%d/%m/%Y")
                st.plotly_chart(aplicar_tema_grafico(fig_v_semana), use_container_width=True, key="9")

            with col_v3:
                st.markdown('<p class="section-title">Chamados por Mês</p>', unsafe_allow_html=True)
                df_tempo['mes'] = df_tempo['data_abertura'].dt.to_period('M').dt.to_timestamp()
                vol_mes = df_tempo.groupby('mes').size().reset_index(name='Qtd')
                fig_v_mes = px.line(vol_mes, x='mes', y='Qtd', markers=True,
                                    color_discrete_sequence=["#f472b6"])
                fig_v_mes.update_xaxes(tickformat="%m/%Y")
                st.plotly_chart(aplicar_tema_grafico(fig_v_mes), use_container_width=True, key="10")

        # Sub-aba: Rankings
        with sub_tab_rankings:
            st.markdown("### 🏆 Top 20 Maiores Volumes")
            col_r1, col_r2, col_r3 = st.columns(3, gap="small")

            with col_r1:
                st.markdown('<p class="section-title">Top 20 Categorias</p>', unsafe_allow_html=True)
                top_cat = df_filtrado['categoria'].value_counts().head(20).reset_index()
                top_cat.columns = ['Categoria', 'Qtd Chamados']
                st.dataframe(top_cat, use_container_width=True, hide_index=True)

            with col_r2:
                st.markdown('<p class="section-title">Top 20 Autores</p>', unsafe_allow_html=True)
                top_aut = df_filtrado['autor'].value_counts().head(20).reset_index()
                top_aut.columns = ['Autor', 'Qtd Aberturas']
                st.dataframe(top_aut, use_container_width=True, hide_index=True)

            with col_r3:
                st.markdown('<p class="section-title">Top 20 Técnicos</p>', unsafe_allow_html=True)
                if df_resolvidos_geral.empty:
                    st.info("Nenhum técnico encontrado para chamados finalizados.")
                else:
                    top_tec = df_resolvidos_geral['resolvido_por'].value_counts().head(20).reset_index()
                    top_tec.columns = ['Técnico', 'Chamados Resolvidos']
                    st.dataframe(top_tec, use_container_width=True, hide_index=True)

# ============================================================
# ─── ABA 5: ANÁLISES ────────────────────────────────────────
# ============================================================
with tab_ana:
    st.markdown('<p class="section-title">💡 Insights e Diagnósticos Automáticos</p>', unsafe_allow_html=True)

    if df_filtrado.empty:
        st.warning("Sem dados suficientes para gerar insights automatizados.")
    else:
        top_comarca    = df_filtrado['comarca'].value_counts().idxmax() if not df_filtrado['comarca'].dropna().empty else "N/A"
        qtd_top_comarca = df_filtrado['comarca'].value_counts().max() if not df_filtrado['comarca'].dropna().empty else 0

        resolvidos_df = df_filtrado[df_filtrado['data_resolucao'].notna()]
        if not resolvidos_df.empty and not resolvidos_df['resolvido_por'].dropna().empty:
            top_tecnico     = resolvidos_df['resolvido_por'].value_counts().idxmax()
            qtd_top_tecnico = resolvidos_df['resolvido_por'].value_counts().max()
        else:
            top_tecnico, qtd_top_tecnico = "N/A", 0

        col_an1, col_an2 = st.columns(2, gap="medium")
        with col_an1:
            st.info(f"📍 **Comarca mais demandada:** **{top_comarca}** com **{formatar_inteiro(qtd_top_comarca)}** chamados.")
        with col_an2:
            st.success(f"🏆 **Técnico com mais entregas:** **{top_tecnico}** com **{formatar_inteiro(qtd_top_tecnico)}** chamados solucionados.")

        st.markdown("---")

        # Categorias Críticas de SLA
        st.markdown("### 🔥 Categorias Críticas (SLA Vencido)")
        cat_counts = df_filtrado['categoria'].value_counts()
        categorias_relevantes = cat_counts[cat_counts > 5].index
        df_relevante = df_filtrado[df_filtrado['categoria'].isin(categorias_relevantes)]

        if not df_relevante.empty:
            sla_por_cat = df_relevante.groupby('categoria')['sla_vencido'].mean().reset_index()
            sla_por_cat['sla_vencido'] = sla_por_cat['sla_vencido'] * 100
            sla_por_cat = sla_por_cat.sort_values(by='sla_vencido', ascending=False).head(5)

            col_g1, col_g2 = st.columns([2, 1], gap="medium")
            with col_g1:
                fig_crit = px.bar(
                    sla_por_cat, x='sla_vencido', y='categoria', orientation='h',
                    title="🔥 Top 5 Categorias — Maior % de SLA Estourado",
                    labels={'sla_vencido': '% de SLA Vencido', 'categoria': 'Categoria'},
                    color='sla_vencido', color_continuous_scale='Reds'
                )
                st.plotly_chart(aplicar_tema_grafico(fig_crit), use_container_width=True, key="11")
            with col_g2:
                st.markdown("""
                **Como interpretar?**

                Estas categorias possuem a maior taxa de descumprimento de prazo de atendimento.

                * Recomenda-se criar procedimentos padrão (playbooks) ou direcionar treinamento específico para a equipe nestes temas.
                """)
        else:
            st.info("Dados insuficientes para calcular volumetria crítica de SLA.")

        st.markdown("---")

        # Reincidências
        st.markdown("### 🔄 Alerta de Possível Reincidência")
        df_reincidentes = (
            df_filtrado.groupby(['usuario', 'categoria']).size()
            .reset_index(name='Repetições')
        )
        df_reincidentes = df_reincidentes[df_reincidentes['Repetições'] > 1].sort_values(
            by='Repetições', ascending=False
        ).head(10)

        if not df_reincidentes.empty:
            col_r1, col_r2 = st.columns([1, 2], gap="medium")
            with col_r1:
                st.markdown("""
                **Detecção de Retrabalho:**

                Usuários que abriram múltiplos chamados sobre a **mesma categoria** — pode indicar:
                1. Chamados fechados sem solução definitiva.
                2. Dificuldade recorrente do usuário.
                3. Gargalo de infraestrutura em lote.
                """)
            with col_r2:
                st.dataframe(df_reincidentes, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Nenhuma reincidência direta detectada no período selecionado.")

        st.markdown("---")

        # Crescimento MoM
        st.markdown("### 📈 Categoria com Maior Crescimento (Mês a Mês)")
        df_tempo2 = df_filtrado.copy()
        df_tempo2['data_abertura'] = pd.to_datetime(df_tempo2['data_abertura'], errors='coerce')
        df_tempo2['mes_ano'] = df_tempo2['data_abertura'].dt.to_period('M')
        meses_disponiveis = sorted(df_tempo2['mes_ano'].dropna().unique())

        if len(meses_disponiveis) >= 2:
            ultimo_mes  = meses_disponiveis[-1]
            mes_anterior = meses_disponiveis[-2]

            df_ult = df_tempo2[df_tempo2['mes_ano'] == ultimo_mes]['categoria'].value_counts().reset_index(name='Qtd_Atual')
            df_ant = df_tempo2[df_tempo2['mes_ano'] == mes_anterior]['categoria'].value_counts().reset_index(name='Qtd_Anterior')
            df_comp = pd.merge(df_ult, df_ant, on='categoria', how='inner')
            df_comp['Diferenca_Absoluta'] = df_comp['Qtd_Atual'] - df_comp['Qtd_Anterior']
            df_comp = df_comp.sort_values(by='Diferenca_Absoluta', ascending=False).head(5)

            if not df_comp.empty:
                fig_cres = px.bar(
                    df_comp, x='Diferenca_Absoluta', y='categoria', orientation='h',
                    title=f"📈 Maior aumento ({mes_anterior.strftime('%m/%Y')} → {ultimo_mes.strftime('%m/%Y')})",
                    labels={'Diferenca_Absoluta': 'Aumento de Chamados (Absoluto)'},
                    color='Diferenca_Absoluta', color_continuous_scale='Bluered'
                )
                st.plotly_chart(aplicar_tema_grafico(fig_cres), use_container_width=True, key="12")
            else:
                st.info("Sem variação significativa entre os últimos meses.")
        else:
            st.info("A análise de crescimento exige pelo menos 2 meses de dados históricos na base ativa.")
