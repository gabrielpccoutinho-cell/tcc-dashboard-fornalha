import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os # Biblioteca adicionada para procurar ficheiros locais

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard Industrial", layout="wide")

st.title("🔥 Monitorização de Caldeira em Tempo Real")
st.markdown("Análise de grandes volumes de dados do processo térmico para identificação de sistemas MIMO.")

# ==========================================
# 1. BARRA LATERAL (CONFIGURAÇÕES E UPLOAD OPCIONAL)
# ==========================================
st.sidebar.header("📁 Fonte de Dados")

# O botão de upload passa a ser opcional
arquivo_csv_upload = st.sidebar.file_uploader("Upload de novo ficheiro (Opcional)", type=['csv'])

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Ajustes de Leitura")
separador = st.sidebar.selectbox("Separador de colunas", [";", ",", "\\t (Tab)"])
decimal = st.sidebar.selectbox("Separador de decimais", [",", "."])

# ==========================================
# 2. MOTOR DE LEITURA OTIMIZADA (CACHE)
# ==========================================
@st.cache_data
def carregar_dados(arquivo, sep, dec):
    if sep == "\\t (Tab)": sep = "\t"
    
    # O pd.read_csv aceita tanto o ficheiro em texto (upload) como o caminho (string)
    df = pd.read_csv(arquivo, sep=sep, decimal=dec)
    
    # Converte a primeira coluna para Data/Hora (forçando o padrão dia/mês)
    nome_coluna_data = df.columns[0]
    df[nome_coluna_data] = pd.to_datetime(df[nome_coluna_data], dayfirst=True, errors='coerce')
    
    # Cria uma coluna oculta apenas com o dia (sem as horas) para facilitar o filtro
    df['Data_Filtragem'] = df[nome_coluna_data].dt.date
    
    return df, nome_coluna_data

# ==========================================
# 3. LÓGICA DE SELEÇÃO DO FICHEIRO
# ==========================================
ficheiro_padrao = "Fornalha.csv"

if arquivo_csv_upload is not None:
    fonte_dados = arquivo_csv_upload
elif os.path.exists(ficheiro_padrao):
    fonte_dados = ficheiro_padrao
else:
    fonte_dados = None

# ==========================================
# 4. RENDERIZAÇÃO DO DASHBOARD
# ==========================================
if fonte_dados is not None:
    try:
        # Carrega os dados da fonte selecionada
        df_completo, col_data = carregar_dados(fonte_dados, separador, decimal)
        
        # --- LÓGICA DO FILTRO DE DATAS ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Filtro de Período")
        
        # Extrai os dias únicos disponíveis no ficheiro
        dias_disponiveis = df_completo['Data_Filtragem'].dropna().unique()
        
        # Formata as opções para o menu (Visão Geral + Datas formatadas)
        opcoes_menu = ["Visão Geral (Todos os Dias)"] + [dia.strftime("%d/%m/%Y") for dia in dias_disponiveis]
        
        # Cria a caixa de seleção no ecrã
        escolha = st.sidebar.selectbox("Selecione a visualização:", opcoes_menu)
        
        # Aplica o filtro no Dataframe
        if escolha == "Visão Geral (Todos os Dias)":
            df_filtrado = df_completo
        else:
            # Converte a escolha de volta para o formato de data e filtra as linhas
            dia_escolhido = pd.to_datetime(escolha, format="%d/%m/%Y").date()
            df_filtrado = df_completo[df_completo['Data_Filtragem'] == dia_escolhido]

        # Verifica se o dataframe não ficou vazio após o filtro
        if df_filtrado.empty:
            st.warning("Não há dados para exibir no período selecionado.")
        else:
            # Pegando na última linha válida para os indicadores (com base no filtro atual)
            ultima_leitura = df_filtrado.iloc[-1]
            
            # -- KPIs --
            st.subheader(f"Indicadores Atuais - {escolha}")
            col1, col2, col3, col4 = st.columns(4)
            
            try:
                temp_atual = ultima_leitura['Temp. Fornalha(ºc)']
                sp_atual = ultima_leitura['Set point(ºc)']
                vel_mat = ultima_leitura['Vel. Material(%)']
                depressao = ultima_leitura['Depressão(mmca)']
                
                col1.metric("Temp. Fornalha", f"{temp_atual} °C", f"{round(temp_atual - sp_atual, 1)} °C do SP", delta_color="inverse")
                col2.metric("Set Point", f"{sp_atual} °C")
                col3.metric("Vel. Material", f"{vel_mat} %")
                col4.metric("Depressão", f"{depressao} mmca")
            except KeyError:
                st.warning("⚠️ Verifique os nomes das colunas na tabela abaixo.")

            st.divider()

            # -- GRÁFICOS INTERATIVOS SINCRONIZADOS (MIMO) --
            st.subheader("Análise Dinâmica Multivariável")
            
            # Cria uma figura com 3 linhas e 1 coluna, partilhando o eixo X (Tempo)
            fig_sync = make_subplots(rows=3, cols=1, 
                                     shared_xaxes=True, 
                                     vertical_spacing=0.05,
                                     subplot_titles=("Temperatura vs Set Point", 
                                                     "Dinâmica de Alimentação e Ar",
                                                     "Controlo de Tiragem (Depressão e Exaustor)"))

            # --- LINHA 1: TEMPERATURA ---
            if 'Temp. Fornalha(ºc)' in df_filtrado.columns:
                fig_sync.add_trace(go.Scatter(x=df_filtrado[col_data], y=df_filtrado['Temp. Fornalha(ºc)'], mode='lines', name='Fornalha', line=dict(color='red', width=2)), row=1, col=1)
            if 'Set point(ºc)' in df_filtrado.columns:
                fig_sync.add_trace(go.Scatter(x=df_filtrado[col_data], y=df_filtrado['Set point(ºc)'], mode='lines', name='SP Temp', line=dict(color='black', dash='dash')), row=1, col=1)

            # --- LINHA 2: ATUADORES DE ENTRADA ---
            if 'Vel. Soprador(%)' in df_filtrado.columns:
                fig_sync.add_trace(go.Scatter(x=df_filtrado[col_data], y=df_filtrado['Vel. Soprador(%)'], mode='lines', name='Vel Soprador', line=dict(color='blue')), row=2, col=1)
            if 'Vel. Material(%)' in df_filtrado.columns:
                fig_sync.add_trace(go.Scatter(x=df_filtrado[col_data], y=df_filtrado['Vel. Material(%)'], mode='lines', name='Vel Material', line=dict(color='orange')), row=2, col=1)

            # --- LINHA 3: TIRAGEM E EXAUSTÃO ---
            if 'Depressão(mmca)' in df_filtrado.columns:
                fig_sync.add_trace(go.Scatter(x=df_filtrado[col_data], y=df_filtrado['Depressão(mmca)'], mode='lines', name='Depressão', line=dict(color='purple')), row=3, col=1)
            if 'SP Depressão(mmca)' in df_filtrado.columns:
                fig_sync.add_trace(go.Scatter(x=df_filtrado[col_data], y=df_filtrado['SP Depressão(mmca)'], mode='lines', name='SP Depressão', line=dict(color='gray', dash='dot')), row=3, col=1)
            if 'Exaustor' in df_filtrado.columns:
                fig_sync.add_trace(go.Scatter(x=df_filtrado[col_data], y=df_filtrado['Exaustor'], mode='lines', name='Exaustor (%)', line=dict(color='green')), row=3, col=1)

            # Ajustes visuais
            fig_sync.update_layout(
                height=800, 
                margin=dict(l=0, r=0, t=40, b=0), 
                hovermode="x unified", 
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_sync, use_container_width=True)

            # -- TABELA EXPLORATÓRIA --
            df_exibicao = df_filtrado.drop(columns=['Data_Filtragem'])
            st.subheader(f"📋 Registos Históricos ({len(df_exibicao)} linhas no filtro atual)")
            st.dataframe(df_exibicao, use_container_width=True, height=300)

    except Exception as e:
        st.error(f"❌ Erro ao processar o ficheiro. Detalhe técnico: {e}")
else:
    st.info("👆 Ficheiro 'Fornalha.csv' não encontrado. Por favor, certifique-se de que está na mesma pasta que o script ou faça o upload manual na barra lateral.")