# pages/6_Visualizar_Feedback.py

import streamlit as st
import pandas as pd
import json
import os

# --- Configuração da Página e Proteção de Acesso ---
st.set_page_config(page_title="Dashboard de Feedback", page_icon="📊")

# Verifica o usuário logado
ADMIN_USERNAME = st.secrets.get("ADMIN_USERNAME", os.getenv("ADMIN_USERNAME"))
username = st.session_state.get("username")

# Proteção de acesso: Apenas o admin pode ver esta página
if username != ADMIN_USERNAME:
    st.error("⛔ Acesso restrito! Esta página é exclusiva para o administrador.")
    st.stop()

# --- Função para Carregar os Dados ---
@st.cache_data(ttl=60)  # Cache para não recarregar o arquivo a cada segundo
def carregar_feedback():
    caminho_arquivo = "dados/feedback.json"
    if os.path.exists(caminho_arquivo):
        try:
            df = pd.read_json(caminho_arquivo, encoding="utf-8")
            return df
        except (ValueError, FileNotFoundError):
            return pd.DataFrame()  # Retorna um DataFrame vazio se o arquivo estiver corrompido ou vazio
    return pd.DataFrame()

# --- Construção do Dashboard ---
st.title("📊 Painel de Feedback dos Usuários")
st.markdown("Analise aqui o que os usuários estão achando do Jarvis.")

df_feedback = carregar_feedback()

# Adiciona o botão de limpar feedbacks
if st.button("Limpar Todos os Feedbacks"):
    caminho_arquivo = "dados/feedback.json"
    with open(caminho_arquivo, "w") as f:
        json.dump([], f)  # Escreve uma lista vazia para remover os dados existentes
    st.success("Feedbacks limpos com sucesso!")
    # Recarrega os feedbacks após a limpeza
    df_feedback = carregar_feedback()

# Verifica se há feedbacks para exibir
if df_feedback.empty:
    st.info("Ainda não há nenhum feedback para exibir. Assim que os usuários enviarem, os dados aparecerão aqui.")
else:
    st.divider()

    # --- Métricas Principais ---
    st.subheader("📈 Métricas Gerais")
    col1, col2 = st.columns(2)

    # Calcula a nota média, tratando o caso de não haver notas ainda
    nota_media = df_feedback['rating'].mean() if not df_feedback['rating'].empty else 0
    total_feedbacks = len(df_feedback)

    with col1:
        st.metric(label="Nota Média Geral", value=f"{nota_media:.2f} ⭐")

    with col2:
        st.metric(label="Total de Feedbacks Recebidos", value=total_feedbacks)

    st.divider()

    # --- Gráfico de Distribuição de Notas ---
    st.subheader("⭐️ Distribuição das Avaliações")

    # Conta a ocorrência de cada nota (1 a 5)
    contagem_notas = df_feedback['rating'].value_counts().sort_index()

    if not contagem_notas.empty:
        st.bar_chart(contagem_notas)
    else:
        st.write("Nenhuma avaliação numérica foi registrada ainda.")

    st.divider()

    # --- Tabela com Comentários ---
    st.subheader("💬 Comentários Detalhados")

    # Filtra para mostrar apenas feedbacks que têm comentários
    df_comentarios = df_feedback[df_feedback['comment'].notna() & (df_feedback['comment'] != '')]

    if not df_comentarios.empty:
        # Exibe a tabela com as colunas mais importantes
        st.dataframe(
            df_comentarios[['timestamp', 'username', 'rating', 'comment']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "timestamp": st.column_config.TextColumn("Data"),
                "username": st.column_config.TextColumn("Usuário"),
                "rating": st.column_config.NumberColumn("Nota", format="%d ⭐"),
                "comment": st.column_config.TextColumn("Comentário", width="large")
            }
        )
    else:
        st.info("Nenhum comentário escrito foi deixado pelos usuários.")