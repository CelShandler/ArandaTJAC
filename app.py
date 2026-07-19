# app.py
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from config import DB_PATH
import importador
from modules.gerador_pdf import gerar_pdf_relatorio

# Configuração da página
st.set_page_config(page_title="TJAC - Chamados BI", layout="wide", initial_sidebar_state="expanded")

# 1. Fluxo de Importação em Background
if 'atualizado' not in st.session_state:
    with st.spinner("Sincronizando base de dados..."):
        st.session_state['atualizado'] = importador.verificar_e_atualizar()

if st.session_state['atualizado']:
    st.toast("Banco de dados atualizado com a última versão do Excel! 🚀")

# Função de leitura rápida (com cache)
@st.cache_data
def carregar_dados_do_banco():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM chamados", conn)
    conn.close()
    
    # Conversões de tipo necessárias pós-banco
    df['data_abertura'] = pd.to_datetime(df['data_abertura'])
    df['data_resolucao'] = pd.to_datetime(df['data_resolucao'])
    df['data_fechamento'] = pd.to_datetime(df['data_fechamento'])
    return df

df = carregar_dados_do_banco()

# 2. Sidebar - Filtros Globais Dinâmicos
st.sidebar.title("Filtros Globais")

# Período
min_dt = df['data_abertura'].min().date() if not df.empty else None
max_dt = df['data_abertura'].max().date() if not df.empty else None
if min_dt and max_dt:
    periodo = st.sidebar.date_input("Período de Abertura", [min_dt, max_dt])
else:
    periodo = None

def filtro_multiselect(label, coluna):
    opcoes = sorted(df[coluna].dropna().unique().tolist())
    return st.sidebar.multiselect(label, opcoes)

grupo_sel = filtro_multiselect("Grupo", "grupo")
categoria_sel = filtro_multiselect("Categoria", "categoria")
comarca_sel = filtro_multiselect("Comarca", "comarca")
tipo_sel = filtro_multiselect("Tipo", "tipo")
prioridade_sel = filtro_multiselect("Prioridade", "prioridade")
estado_sel = filtro_multiselect("Estado", "estado")
autor_sel = filtro_multiselect("Autor", "autor")
resolvido_sel = filtro_multiselect("Resolvido por", "resolvido_por")
cidade_sel = filtro_multiselect("Cidade", "cidade_cliente")

# Aplicação dos Filtros Ativos
df_filtrado = df.copy()
if periodo and len(periodo) == 2:
    df_filtrado = df_filtrado[
        (df_filtrado['data_abertura'].dt.date >= periodo[0]) & 
        (df_filtrado['data_abertura'].dt.date <= periodo[1])
    ]
if grupo_sel:
    df_filtrado = df_filtrado[df_filtrado['grupo'].isin(grupo_sel)]
if categoria_sel:
    df_filtrado = df_filtrado[df_filtrado['categoria'].isin(categoria_sel)]
if comarca_sel:
    df_filtrado = df_filtrado[df_filtrado['comarca'].isin(comarca_sel)]
if tipo_sel:
    df_filtrado = df_filtrado[df_filtrado['tipo'].isin(tipo_sel)]
if prioridade_sel:
    df_filtrado = df_filtrado[df_filtrado['prioridade'].isin(prioridade_sel)]
if estado_sel:
    df_filtrado = df_filtrado[df_filtrado['estado'].isin(estado_sel)]
if autor_sel:
    df_filtrado = df_filtrado[df_filtrado['autor'].isin(autor_sel)]
if resolvido_sel:
    df_filtrado = df_filtrado[df_filtrado['resolvido_por'].isin(resolvido_sel)]
if cidade_sel:
    df_filtrado = df_filtrado[df_filtrado['cidade_cliente'].isin(cidade_sel)]

# 3. Definição das Abas do Painel
tab_dash, tab_rel, tab_busca, tab_ind, tab_ana = st.tabs([
    "📊 Dashboard", 
    "🗂️ Relatórios", 
    "🔍 Pesquisar Chamado", 
    "📈 Indicadores", 
    "💡 Análises"
])

with tab_dash:
    st.subheader("Indicadores de Atendimento")

    # KPIs Dinâmicos
    total_chamados = len(df_filtrado)
    resolvidos = len(df_filtrado[df_filtrado['data_resolucao'].notna()])
    vencidos = len(df_filtrado[df_filtrado['sla_vencido'] == 1])
    cumpridos = total_chamados - vencidos
    
    sla_cumprido_pct = (cumpridos / total_chamados * 100) if total_chamados > 0 else 100
    sla_vencido_pct = (vencidos / total_chamados * 100) if total_chamados > 0 else 0

    # Tempo Médio de Resolução (em horas)
    df_resolvidos = df_filtrado[df_filtrado['data_resolucao'].notna() & df_filtrado['data_abertura'].notna()].copy()
    if not df_resolvidos.empty:
        df_resolvidos['tempo_res'] = (df_resolvidos['data_resolucao'] - df_resolvidos['data_abertura']).dt.total_seconds() / 3600
        tempo_medio = f"{df_resolvidos['tempo_res'].mean():.1f}h"
    else:
        tempo_medio = "N/A"

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total de Chamados", f"{total_chamados:,}")
    col2.metric("Resolvidos", f"{resolvidos:,}")
    col3.metric("SLA Cumprido %", f"{sla_cumprido_pct:.1f}%")
    col4.metric("SLA Vencido %", f"{sla_vencido_pct:.1f}%")
    col5.metric("Tempo Médio Resolução", tempo_medio)

    st.markdown("---")

    # Gráficos em Grid
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        # Gráfico 1: Chamados por mês
        df_mes = df_filtrado.groupby(df_filtrado['data_abertura'].dt.to_period("M")).size().reset_index(name='Qtd')
        df_mes['data_abertura'] = df_mes['data_abertura'].astype(str)
        fig_mes = px.line(df_mes, x='data_abertura', y='Qtd', title="Evolução Mensal de Abertura", markers=True)
        st.plotly_chart(fig_mes, use_container_width=True, key="1")

        # Gráfico 2: Top 15 Categorias
        df_cat = df_filtrado['categoria'].value_counts().reset_index(name='Qtd').head(15)
        fig_cat = px.bar(df_cat, x='categoria', y='Qtd', title="Top 15 Categorias de Chamados", color='Qtd')
        st.plotly_chart(fig_cat, use_container_width=True, key="2")

    with g_col2:
        # Gráfico 3: SLA Pizza
        fig_sla = px.pie(names=['Cumprido', 'Vencido'], values=[cumpridos, vencidos], title="Status de SLA", hole=0.4)
        st.plotly_chart(fig_sla, use_container_width=True, key="3")

        # Gráfico 4: Comarcas (Barra Horizontal)
        df_comarca = df_filtrado['comarca'].value_counts().reset_index(name='Qtd').head(10)
        fig_comarca = px.bar(df_comarca, x='Qtd', y='comarca', orientation='h', title="Top Comarcas", color='Qtd')
        fig_comarca.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_comarca, use_container_width=True, key="4")

with tab_rel:
    st.subheader("Gerador de Relatórios Customizados")

    col_config, col_preview = st.columns([1, 3])

    with col_config:
        st.markdown("**1. Escolha as Colunas para Exibição**")
        # colunas_disponiveis = {
        #     "Número": "numero", "Data Abertura": "data_abertura", "Grupo": "grupo",
        #     "Categoria": "categoria", "Comarca": "comarca", "Autor": "autor",
        #     "Resolvido Por": "resolvido_por", "Estado": "estado", "SLA Vencido": "sla_vencido"
        # }
        colunas_disponiveis = {
            "Número": "numero", "Data Abertura": "data_abertura", "Grupo": "grupo",
            "Categoria": "categoria", "Comarca": "comarca", "Autor": "autor",
            "Resolvido Por": "resolvido_por", "Estado": "estado", "SLA Vencido": "sla_vencido",
            "IP do Usuário": "user_ip", "Login": "user_login", "Nome Completo": "user_nome",
            "Patrimônio": "user_patrimonio", "Setor": "user_setor", "Ramal": "user_ramal"
        }




        selecionadas_nomes = []
        for nome in colunas_disponiveis.keys():
            if st.checkbox(nome, value=nome in ["Número", "Data Abertura", "Grupo", "Categoria", "Comarca"]):
                selecionadas_nomes.append(nome)
        
        colunas_db = [colunas_disponiveis[n] for n in selecionadas_nomes]

        st.markdown("---")
        st.markdown("**2. Agrupamento Opcional**")
        agrupamento = st.multiselect("Agrupar dados por:", ["grupo", "comarca", "resolvido_por", "categoria", "estado"])

        st.markdown("---")
        ordenacao = st.radio("Ordenação de Registros", ["Crescente", "Decrescente"])

    with col_preview:
        if df_filtrado.empty:
            st.warning("Nenhum dado encontrado com os filtros globais aplicados.")
        else:
            # Lógica de agrupamento ou raw data
            if agrupamento:
                df_rel = df_filtrado.groupby(agrupamento).size().reset_index(name="Quantidade Total")
                df_rel = df_rel.sort_values(by="Quantidade Total", ascending=(ordenacao == "Crescente"))
            else:
                df_rel = df_filtrado[colunas_db].copy()
                if "data_abertura" in colunas_db:
                    df_rel = df_rel.sort_values(by="data_abertura", ascending=(ordenacao == "Crescente"))

            # Mostra prévia na tela
            st.dataframe(df_rel, use_container_width=True, hide_index=True)

            # --- SESSÃO DE EXPORTAÇÃO (Excel, CSV e PDF) ---
            st.markdown("### 📥 Exportar Relatório Filtrado")
            exp_col1, exp_col2, exp_col3 = st.columns(3)
            
            # 1. Exportação em CSV
            csv_data = df_rel.to_csv(index=False, sep=";", encoding="utf-8-sig").encode('utf-8-sig')
            exp_col1.download_button(
                label="📄 Baixar CSV", 
                data=csv_data, 
                file_name="relatorio_tj.csv", 
                mime="text/csv"
            )
            
            # 2. Exportação em Excel (usando io.BytesIO para manter em memória)
            import io
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_rel.to_excel(writer, index=False, sheet_name='Chamados Filtrados')
            excel_data = output_excel.getvalue()
            
            exp_col2.download_button(
                label="📊 Baixar Excel", 
                data=excel_data, 
                file_name="relatorio_tj.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # 3. Exportação em PDF Dinâmico
            with st.spinner("Preparando motor de PDF..."):
                pdf_bytes = gerar_pdf_relatorio(df=df_rel, agrupamento=agrupamento)
                
                exp_col3.download_button(
                    label="📕 Baixar PDF Oficial",
                    data=pdf_bytes,
                    file_name="relatorio_oficial_tj.pdf",
                    mime="application/pdf"
                )

with tab_busca:
    st.subheader("Pesquisa Textual Inteligente (Indexada)")
    
    termo_pesquisa = st.text_input("Digite o termo (Número, Autor, Descrição, IP, AnyDesk, CPF, etc.):", "")

    if termo_pesquisa:
        conn = sqlite3.connect(DB_PATH)
        # Tenta usar a tabela FTS5 virtual, caso contrário faz fallback para LIKE no banco convencional
        try:
            query = """
                SELECT c.* FROM chamados c
                JOIN chamados_fts f ON c.id = f.id
                WHERE chamados_fts MATCH ?
            """
            df_busca = pd.read_sql_query(query, conn, params=(f"*{termo_pesquisa}*",))
        except Exception:
            # Fallback seguro caso a extensão FTS5 não esteja disponível no seu SQLite local
            # query = """
            #     SELECT * FROM chamados 
            #     WHERE numero LIKE ? 
            #        OR autor LIKE ? 
            #        OR descricao LIKE ? 
            #        OR resolvido_por LIKE ? 
            #        OR comarca LIKE ?
            # """
            # param = f"%{termo_pesquisa}%"
            # df_busca = pd.read_sql_query(query, conn, params=(param, param, param, param, param))
            query = """
                SELECT * FROM chamados 
                WHERE numero LIKE ? OR autor LIKE ? OR descricao LIKE ? OR resolvido_por LIKE ? 
                OR comarca LIKE ? OR user_ip LIKE ? OR user_patrimonio LIKE ? OR user_login LIKE ?
            """
            param = f"%{termo_pesquisa}%"
            df_busca = pd.read_sql_query(query, conn, params=(param, param, param, param, param, param, param, param))

        conn.close()

        if not df_busca.empty:
            st.write(f"Foram encontrados **{len(df_busca)}** chamados relacionados a '{termo_pesquisa}':")
            st.dataframe(df_busca, use_container_width=True)
        else:
            st.info("Nenhum registro encontrado para essa busca.")

with tab_ind:
    st.subheader("Métricas de Desempenho e Produtividade")
    
    if df_filtrado.empty:
        st.warning("Sem dados disponíveis para calcular os indicadores com os filtros atuais.")
    else:
        # --- MOTOR DE INTELIGÊNCIA TEMPORAL (BLINDADO) ---
        df_tempo = df_filtrado.copy()
        df_tempo['data_abertura'] = pd.to_datetime(df_tempo['data_abertura'], errors='coerce')
        df_tempo['data_resolucao'] = pd.to_datetime(df_tempo['data_resolucao'], errors='coerce')
        df_tempo['data_fechamento'] = pd.to_datetime(df_tempo['data_fechamento'], errors='coerce')

        # Regra de Ouro: Identifica resolvidos por Status OR por presença de Datas Fim
        status_resolvido = df_tempo['estado'].astype(str).str.upper().str.strip().isin(['RESOLVED', 'RESOLVIDO', 'FECHADO', 'CLOSED'])
        tem_data_fim = df_tempo['data_resolucao'].notna() | df_tempo['data_fechamento'].notna()
        
        # Cria o DataFrame Oficial de Resolvidos
        df_resolvidos_geral = df_tempo[status_resolvido | tem_data_fim].copy()

        # Elege a melhor data de finalização disponível para não zerar os cálculos de tempo
        df_resolvidos_geral['data_fim_efetiva'] = df_resolvidos_geral['data_resolucao'].fillna(df_resolvidos_geral['data_fechamento'])
        
        # Filtra quem tem datas válidas de abertura e fim para calcular a métrica de horas
        df_com_tempo = df_resolvidos_geral[df_resolvidos_geral['data_abertura'].notna() & df_resolvidos_geral['data_fim_efetiva'].notna()].copy()
        df_com_tempo['tempo_horas'] = (df_com_tempo['data_fim_efetiva'] - df_com_tempo['data_abertura']).dt.total_seconds() / 3600
        
        # Evita distorções de registros com datas inconsistentes (ex: data fim menor que abertura)
        df_com_tempo = df_com_tempo[df_com_tempo['tempo_horas'] >= 0]

        # --- INTERFACE GRÁFICA DAS SUB-ABAS ---
        sub_tab_tempo, sub_tab_vol, sub_tab_rankings = st.tabs([
            "⏱️ Tempos Médios de Atendimento", 
            "📅 Evolução Temporal (Volume)", 
            "🏆 Rankings (Top 20)"
        ])

        # --- SUB-ABA 1: TEMPOS MÉDIOS ---
        with sub_tab_tempo:
            st.markdown("### Tempo Médio de Resolução (em Horas)")
            
            if df_com_tempo.empty:
                st.info("💡 Os chamados estão marcados como resolvidos, mas as colunas de data de resolução/fechamento estão ausentes ou inconsistentes no Excel para calcular médias de tempo.")
            else:
                col_t1, col_t2, col_t3 = st.columns(3)

                with col_t1:
                    st.markdown("**Por Comarca**")
                    tempo_comarca = df_com_tempo.groupby('comarca')['tempo_horas'].mean().reset_index()
                    tempo_comarca = tempo_comarca.sort_values(by='tempo_horas', ascending=False)
                    fig_t_comarca = px.bar(tempo_comarca, x='tempo_horas', y='comarca', orientation='h', 
                                           labels={'tempo_horas': 'Horas Médias', 'comarca': 'Comarca'},
                                           color='tempo_horas', color_continuous_scale='Reds')
                    st.plotly_chart(fig_t_comarca, use_container_width=True, key="5")

                with col_t2:
                    st.markdown("**Por Técnico**")
                    tempo_tecnico = df_com_tempo.groupby('resolvido_por')['tempo_horas'].mean().reset_index()
                    tempo_tecnico = tempo_tecnico.sort_values(by='tempo_horas', ascending=False).head(15)
                    fig_t_tec = px.bar(tempo_tecnico, x='tempo_horas', y='resolvido_por', orientation='h',
                                       labels={'tempo_horas': 'Horas Médias', 'resolvido_por': 'Técnico'},
                                       color='tempo_horas', color_continuous_scale='Oranges')
                    st.plotly_chart(fig_t_tec, use_container_width=True, key="6")

                with col_t3:
                    st.markdown("**Por Categoria**")
                    tempo_cat = df_com_tempo.groupby('categoria')['tempo_horas'].mean().reset_index()
                    tempo_cat = tempo_cat.sort_values(by='tempo_horas', ascending=False).head(15)
                    fig_t_cat = px.bar(tempo_cat, x='tempo_horas', y='categoria', orientation='h',
                                       labels={'tempo_horas': 'Horas Médias', 'categoria': 'Categoria'},
                                       color='tempo_horas', color_continuous_scale='Purples')
                    st.plotly_chart(fig_t_cat, use_container_width=True, key="7")

        # --- SUB-ABA 2: EVOLUÇÃO TEMPORAL ---
        with sub_tab_vol:
            st.markdown("### Análise de Tendência de Aberturas")
            
            col_v1, col_v2, col_v3 = st.columns(3)
            
            with col_v1:
                st.markdown("**Chamados por Dia**")
                vol_dia = df_tempo.groupby(df_tempo['data_abertura'].dt.date).size().reset_index(name='Qtd')
                fig_v_dia = px.line(vol_dia, x='data_abertura', y='Qtd', markers=True)
                st.plotly_chart(fig_v_dia, use_container_width=True, key="8")

            with col_v2:
                st.markdown("**Chamados por Semana**")
                df_tempo['semana'] = df_tempo['data_abertura'].dt.to_period('W').dt.to_timestamp()
                vol_semana = df_tempo.groupby('semana').size().reset_index(name='Qtd')
                fig_v_semana = px.line(vol_semana, x='semana', y='Qtd', markers=True, color_discrete_sequence=['green'])
                st.plotly_chart(fig_v_semana, use_container_width=True, key="9")

            with col_v3:
                st.markdown("**Chamados por Mês**")
                df_tempo['mes'] = df_tempo['data_abertura'].dt.to_period('M').dt.to_timestamp()
                vol_mes = df_tempo.groupby('mes').size().reset_index(name='Qtd')
                fig_v_mes = px.line(vol_mes, x='mes', y='Qtd', markers=True, color_discrete_sequence=['red'])
                st.plotly_chart(fig_v_mes, use_container_width=True, key="10")

        # --- SUB-ABA 3: RANKINGS (AGORA SINTONIZADA COM O ESTADO DO CHAMADO) ---
        with sub_tab_rankings:
            st.markdown("### Top 20 Maiores Volumes")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.markdown("**Top 20 Categorias (Geral)**")
                top_cat = df_filtrado['categoria'].value_counts().head(20).reset_index()
                top_cat.columns = ['Categoria', 'Qtd Chamados']
                st.dataframe(top_cat, use_container_width=True, hide_index=True)
                
            with col_r2:
                st.markdown("**Top 20 Autores (Quem mais abre)**")
                top_aut = df_filtrado['autor'].value_counts().head(20).reset_index()
                top_aut.columns = ['Autor', 'Qtd Aberturas']
                st.dataframe(top_aut, use_container_width=True, hide_index=True)
                
            with col_r3:
                st.markdown("**Top 20 Técnicos (Quem mais resolve)**")
                if df_resolvidos_geral.empty:
                    st.info("Nenhum técnico encontrado para chamados finalizados.")
                else:
                    # Contabiliza a partir do DataFrame unificado de resolvidos
                    top_tec = df_resolvidos_geral['resolvido_por'].value_counts().head(20).reset_index()
                    top_tec.columns = ['Técnico', 'Chamados Resolvidos']
                    st.dataframe(top_tec, use_container_width=True, hide_index=True)


with tab_ana:
    st.subheader("💡 Insights e Diagnósticos Automáticos")
    
    if df_filtrado.empty:
        st.warning("Sem dados suficientes para gerar insights automatizados.")
    else:
        # 1. Comarca com mais chamados (Destaque)
        top_comarca = df_filtrado['comarca'].value_counts().idxmax() if not df_filtrado['comarca'].dropna().empty else "N/A"
        qtd_top_comarca = df_filtrado['comarca'].value_counts().max() if not df_filtrado['comarca'].dropna().empty else 0
        
        # 2. Técnico mais produtivo (mais resoluções resolvidas)
        resolvidos_df = df_filtrado[df_filtrado['data_resolucao'].notna()]
        if not resolvidos_df.empty and not resolvidos_df['resolvido_por'].dropna().empty:
            top_tecnico = resolvidos_df['resolvido_por'].value_counts().idxmax()
            qtd_top_tecnico = resolvidos_df['resolvido_por'].value_counts().max()
        else:
            top_tecnico, qtd_top_tecnico = "N/A", 0

        # Mostra os Destaques Rápidos
        col_an1, col_an2 = st.columns(2)
        with col_an1:
            st.info(f"📍 **Comarca mais demandada:** **{top_comarca}** com **{qtd_top_comarca}** chamados abertos.")
        with col_an2:
            st.success(f"🏆 **Técnico com mais entregas:** **{top_tecnico}** com **{qtd_top_tecnico}** chamados solucionados.")

        st.markdown("---")

        # 3. Categorias Críticas (Alto índice de estouro de SLA)
        st.markdown("### 🔥 Categorias Críticas (SLA Vencido)")
        # Agrupa categorias com mais de 5 chamados para evitar distorções estatísticas (ex: 1 chamado aberto e 1 vencido = 100%)
        cat_counts = df_filtrado['categoria'].value_counts()
        categorias_relevantes = cat_counts[cat_counts > 5].index
        
        df_relevante = df_filtrado[df_filtrado['categoria'].isin(categorias_relevantes)]
        
        if not df_relevante.empty:
            sla_por_cat = df_relevante.groupby('categoria')['sla_vencido'].mean().reset_index()
            sla_por_cat['sla_vencido'] = sla_por_cat['sla_vencido'] * 100 # Transforma em %
            sla_por_cat = sla_por_cat.sort_values(by='sla_vencido', ascending=False).head(5)
            
            col_g1, col_g2 = st.columns([2, 1])
            with col_g1:
                fig_crit = px.bar(sla_por_cat, x='sla_vencido', y='categoria', orientation='h',
                                  title="Top 5 Categorias com Maior % de SLA Estourado",
                                  labels={'sla_vencido': '% de SLA Vencido', 'categoria': 'Categoria'},
                                  color='sla_vencido', color_continuous_scale='Reds')
                st.plotly_chart(fig_crit, use_container_width=True, key="11")
            with col_g2:
                st.markdown("""
                **Como interpretar?**
                Estas categorias possuem a maior taxa de descumprimento de prazo de atendimento. 
                * Recomenda-se criar procedimentos padrão (playbooks) ou direcionar treinamento específico para a equipe de atendimento nestes temas.
                """)
        else:
            st.info("Dados insuficientes para calcular volumetria crítica de SLA.")

        st.markdown("---")

        # 4. Chamados Possivelmente Reincidentes
        # Identifica usuários que abriram mais de 1 chamado para a mesma categoria em um intervalo curto
        st.markdown("### 🔄 Alerta de Possível Reincidência")
        
        # Agrupa por Usuário e Categoria
        df_reincidentes = df_filtrado.groupby(['usuario', 'categoria']).size().reset_index(name='Repetições')
        df_reincidentes = df_reincidentes[df_reincidentes['Repetições'] > 1].sort_values(by='Repetições', ascending=False).head(10)
        
        if not df_reincidentes.empty:
            col_r1, col_r2 = st.columns([1, 2])
            with col_r1:
                st.markdown("""
                **Detecção de Retrabalho:**
                A tabela ao lado lista usuários que abriram múltiplos chamados sobre a **mesma categoria**. 
                
                Isso pode indicar:
                1. Chamados fechados sem solução definitiva.
                2. Dificuldade recorrente do usuário com o mesmo sistema/equipamento.
                3. Gargalo de infraestrutura em lote.
                """)
            with col_r2:
                st.dataframe(df_reincidentes, use_container_width=True, hide_index=True)
        else:
            st.success("Excelente! Nenhuma reincidência direta (mesmo usuário abrindo mesma categoria repetidamente) foi detectada.")

        st.markdown("---")

        # 5. Categoria com maior crescimento (MoM - Mês contra Mês)
        st.markdown("### 📈 Categoria com Maior Crescimento")
        df_tempo['mes_ano'] = df_tempo['data_abertura'].dt.to_period('M')
        meses_disponiveis = sorted(df_tempo['mes_ano'].unique())
        
        if len(meses_disponiveis) >= 2:
            ultimo_mes = meses_disponiveis[-1]
            mes_anterior = meses_disponiveis[-2]
            
            # Filtra e conta
            df_ult = df_tempo[df_tempo['mes_ano'] == ultimo_mes]['categoria'].value_counts().reset_index(name='Qtd_Atual')
            df_ant = df_tempo[df_tempo['mes_ano'] == mes_anterior]['categoria'].value_counts().reset_index(name='Qtd_Anterior')
            
            df_comp = pd.merge(df_ult, df_ant, on='categoria', how='inner')
            df_comp['Diferenca_Absoluta'] = df_comp['Qtd_Atual'] - df_comp['Qtd_Anterior']
            df_comp = df_comp.sort_values(by='Diferenca_Absoluta', ascending=False).head(5)
            
            if not df_comp.empty:
                fig_cres = px.bar(df_comp, x='Diferenca_Absoluta', y='categoria', orientation='h',
                                  title=f"Maior aumento de chamados ({mes_anterior} vs {ultimo_mes})",
                                  labels={'Diferenca_Absoluta': 'Aumento de Chamados (Absoluto)'},
                                  color='Diferenca_Absoluta', color_continuous_scale='Bluered')
                st.plotly_chart(fig_cres, use_container_width=True, key="12")
            else:
                st.info("Sem variação significativa entre os últimos meses.")
        else:
            st.info("A análise de crescimento (Mês a Mês) exige pelo menos 2 meses de dados históricos na base ativa.")

