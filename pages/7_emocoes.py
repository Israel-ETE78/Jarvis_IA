import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils import carregar_emocoes, salvar_emocoes, carregar_reflexoes, salvar_reflexoes
from auth import get_current_username
import requests
import os
import json

st.set_page_config(page_title="Jarvis – Painel Emocional", layout="wide")
st.title("🧠 Jarvis – Painel Emocional com Apoio Pessoal")

# --- Botão discreto para voltar ao chat principal ---
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.switch_page("app.py")

username = get_current_username()
# Carrega as emoções (pode conter formatos mistos: dicionário ou string)
emocoes_dict_raw = carregar_emocoes(username)

if not emocoes_dict_raw:
    st.info("Nenhum dado emocional registrado ainda. Interaja no chat para que eu detecte automaticamente 💙")
    st.stop()

# --- INÍCIO DA CORREÇÃO CIRÚRGICA: Normalização e Criação do DataFrame ---
normalized_emocoes_list = []
for timestamp, data in emocoes_dict_raw.items():
    entry = {"timestamp": timestamp}
    if isinstance(data, dict):
        # Se for um dicionário, extrai as chaves e valores
        entry.update(data)
        # Garante que a chave 'emocao' exista e seja uma string, convertendo para minúsculas
        entry['emocao'] = str(entry.get('emocao', 'desconhecida')).lower()
        # Fallback para outras chaves de sentimento se 'emocao' não for encontrada
        if entry['emocao'] == 'desconhecida':
            if 'sentimento_mensagem_usuario' in entry and isinstance(entry['sentimento_mensagem_usuario'], str):
                entry['emocao'] = entry['sentimento_mensagem_usuario'].lower()
            elif 'sentimento' in entry and isinstance(entry['sentimento'], str):
                entry['emocao'] = entry['sentimento'].lower()
    elif isinstance(data, str):
        # Se for uma string (formato antigo), cria um dicionário padrão
        entry['emocao'] = data.lower()
        entry['sentimento_mensagem_usuario'] = "Não disponível"
        entry['tipo_interacao'] = "Não disponível"
        entry['topico_interacao'] = "Não disponível"
        entry['dia_da_semana'] = "Não disponível"
        entry['periodo_do_dia'] = "Não disponível"
        entry['prompt_original'] = "Não disponível"
        
        # Tenta inferir dia da semana e período do dia para entradas antigas
        try:
            ts_obj = pd.to_datetime(timestamp, errors='coerce')
            if pd.notna(ts_obj):
                entry["dia_da_semana"] = ts_obj.strftime('%A').lower()
                hora = ts_obj.hour
                if 5 <= hora < 12: entry["periodo_do_dia"] = "manhã"
                elif 12 <= hora < 18: entry["periodo_do_dia"] = "tarde"
                else: entry["periodo_do_dia"] = "noite"
        except Exception as e:
            print(f"Erro ao inferir data/hora para timestamp {timestamp}: {e}")

    normalized_emocoes_list.append(entry)

# Cria o DataFrame a partir da lista normalizada de dicionários
df = pd.DataFrame(normalized_emocoes_list)

# Converte a coluna timestamp para datetime, lidando com formatos mistos
df["timestamp"] = pd.to_datetime(df["timestamp"], format='mixed', errors='coerce')
df = df.dropna(subset=['timestamp']) # Remove linhas com timestamps inválidos

# Garante que 'emocao' seja string e ordena por timestamp
df['emocao'] = df['emocao'].astype(str)
df = df.sort_values("timestamp", ascending=True)

# Pega a última emoção depois da normalização e ordenação
ultima_emocao = df.iloc[-1]["emocao"] if not df.empty and "emocao" in df.columns else None
# --- FIM DA CORREÇÃO CIRÚRGICA: Normalização e Criação do DataFrame ---

# === DIAGNÓSTICO EMOCIONAL VISUAL ===
# Garante que 'ultimos_10' seja processado a partir do df normalizado e limpo
ultimos_10 = df["emocao"].tail(10).tolist() if "emocao" in df.columns else []
# Define 'ultimos' no escopo global para uso no alerta de risco
ultimos = df["emocao"].tail(5).tolist() if "emocao" in df.columns else []


positivas = ["feliz", "grato", "animado"]
negativas = ["triste", "desesperado", "suicida", "cansado", "esgotado", "irritado", "raivoso"]
alerta = ["ansioso", "preocupado"]

estado = "Neutro"
cor = "#B0BEC5"  # cinza claro

if any(e in ultimos_10 for e in negativas):
    estado = "Ruim"
    cor = "#EF5350"  # vermelho
elif any(e in ultimos_10 for e in alerta):
    estado = "Atenção"
    cor = "#FFB300"  # amarelo
elif any(e in ultimos_10 for e in positivas):
    estado = "Bom"
    cor = "#66BB6A"  # verde

with st.container():
    st.markdown(f"""
    <div style='background-color:{cor};padding:15px;border-radius:8px;text-align:center;'>
        <h3 style='color:white;margin:0;'>Estado Emocional Atual: {estado.upper()}</h3>
        <small style='color:white;'>Com base nas últimas 10 emoções registradas</small>
    </div>
    """, unsafe_allow_html=True)

# =======================================================
# === FUNÇÃO PARA BUSCA DINÂMICA VIA SERPER API ===
# =======================================================

SERPER_API_KEY = st.secrets.get("SERPER_API_KEY") or os.getenv("SERPER_API_KEY")
SERPER_API_ENDPOINT_VIDEOS = "https://google.serper.dev/videos"
SERPER_API_ENDPOINT_SEARCH = "https://google.serper.dev/search"

def search_content_via_serper_api(query, content_type="video", max_results=1):
    """
    Pesquisa conteúdo relevante usando a Serper API.

    Args:
        query (str): O termo de busca.
        content_type (str): Tipo de conteúdo preferencial ("video", "general").
        max_results (int): Número máximo de resultados desejados.

    Returns:
        str: A URL do conteúdo mais relevante, ou None se não encontrar.
    """
    if not SERPER_API_KEY:
        print("Chave da SERPER_API_KEY não configurada. Por favor, configure-a.")
        return None

    if content_type == "video":
        api_url = SERPER_API_ENDPOINT_VIDEOS
        payload = json.dumps({"q": query, "num": max_results})
    else: # content_type == "general" ou qualquer outro
        api_url = SERPER_API_ENDPOINT_SEARCH
        payload = json.dumps({"q": query, "num": max_results})

    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(api_url, headers=headers, data=payload, timeout=10)
        response.raise_for_status() # Lança um erro para status de resposta HTTP ruins (4xx ou 5xx)

        data = response.json()

        if content_type == "video":
            if data and data.get("videos"):
                first_video = data["videos"][0]
                if "link" in first_video:
                    return first_video["link"]
        else: # Busca geral
            if data and data.get("organic"):
                first_result = data["organic"][0]
                if "link" in first_result:
                    return first_result["link"]
        return None

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição à Serper API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON da Serper API: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao buscar conteúdo via Serper API: {e}")
        return None


# =======================================================
# === Função de recomendação personalizada (AGORA USA A SERPER API) ===
# =======================================================
def gerar_recomendacao_emocional(df_emocoes):
    if df_emocoes.empty:
        return None, None

    # Certifique-se de que ultima_emocao seja uma string antes de usar .lower()
    ultima = df_emocoes.iloc[-1]["emocao"].lower() if "emocao" in df_emocoes.columns and not df_emocoes.empty else None
    
    # Certifique-se de que a coluna 'emocao' contenha strings antes de chamar .str.lower()
    # Esta variável 'ultimos_local' é para uso interno da função, não confundir com a global
    ultimos_local = df_emocoes["emocao"].astype(str).tail(5).str.lower().tolist()

    recomendacoes = {
        "triste": {
            "mensagem": "🚨 Percebo uma sequência de tristeza. Você não está só. Recomendo este apoio imediato:",
            "query": "vídeos de apoio para tristeza e desânimo"
        },
        "desesperado": {
            "mensagem": "⚠️ Estou aqui com você. Essa é uma situação que precisa de acolhimento humano. Por favor, procure apoio agora:",
            "link": "https://www.cvv.org.br" # Mantido fixo para recursos críticos
        },
        "suicida": {
            "mensagem": "⚠️ Estou aqui com você. Essa é uma situação que precisa de acolhimento humano. Por favor, procure apoio agora:",
            "link": "https://www.cvv.org.br" # Mantido fixo para recursos críticos
        },
        "ansioso": {
            "mensagem": "🌬️ Uma técnica de respiração pode te ajudar agora. Respire comigo:",
            "query": "exercícios de respiração para ansiedade"
        },
        "preocupado": {
            "mensagem": "🌬️ Uma técnica de respiração pode te ajudar agora. Respire comigo:",
            "query": "exercícios de respiração para acalmar a mente"
        },
        "cansado": {
            "mensagem": "😴 Você merece um descanso. Essa música ambiente ajuda a recarregar a mente:",
            "query": "música relaxante para dormir"
        },
        "esgotado": {
            "mensagem": "😴 Você merece um descanso. Essa música ambiente ajuda a recarregar a mente:",
            "query": "música para relaxar e recarregar energias"
        },
        "irritado": {
            "mensagem": "⚡ Canalize sua raiva com clareza. Essa explicação pode te ajudar:",
            "query": "como lidar com a raiva técnicas"
        },
        "raivoso": {
            "mensagem": "⚡ Canalize sua raiva com clareza. Essa explicação pode te ajudar:",
            "query": "gerenciamento da raiva dicas"
        },
        "feliz": {
            "mensagem": "🌈 Que bom te ver assim! Continue espalhando luz. Uma música suave para manter esse clima:",
            "query": "música positiva para bem estar"
        },
        "grato": {
            "mensagem": "🌈 Que bom te ver assim! Continue espalhando luz. Uma música suave para manter esse clima:",
            "query": "música inspiradora para gratidão"
        },
        "animado": {
            "mensagem": "🌈 Que bom te ver assim! Continue espalhando luz. Uma música suave para manter esse clima:",
            "query": "música alegre e motivadora"
        }
    }

    link_encontrado = None
    mensagem_final = None
    query_para_busca = None

    # Primeiro, verifica a última emoção para recomendação direta
    if ultima in recomendacoes: 
        config = recomendacoes[ultima]
        mensagem_final = config["mensagem"]
        if "link" in config:
            link_encontrado = config["link"]
        else:
            query_para_busca = config["query"]

    # Em seguida, sobrepõe com a condição de tristeza persistente, se aplicável
    if ultimos_local.count("triste") >= 3:
        mensagem_final = recomendacoes["triste"]["mensagem"]
        query_para_busca = recomendacoes["triste"]["query"]
        link_encontrado = None # Garante que a busca seja feita para esta condição

    # Se uma query foi definida e nenhum link fixo foi encontrado, faça a busca
    if query_para_busca and not link_encontrado:
        if "vídeos" in query_para_busca.lower() or "música" in query_para_busca.lower():
            link_encontrado = search_content_via_serper_api(query_para_busca, content_type="video")
        else:
            link_encontrado = search_content_via_serper_api(query_para_busca, content_type="general")

    # Caso não caia em nenhuma das condições específicas ou se a busca falhar, use um padrão
    if not link_encontrado:
        mensagem_final = "💬 Você está em equilíbrio. Se quiser, aqui vai um conteúdo para manter o bem-estar:"
        link_encontrado = search_content_via_serper_api("conteúdo sobre bem-estar e saúde mental", content_type="general")
        if not link_encontrado: # Fallback caso a busca final também falhe
            link_encontrado = "https://www.google.com/search?q=conte%C3%Bado+para+bem+estar" # Exemplo de busca genérica no Google

    if link_encontrado:
        return mensagem_final, link_encontrado
    else:
        return None, None

# Supondo que 'df' e 'ultima_emocao' já estejam definidos em seu código
# Antes da parte de visualização, chame a função de recomendação
recomendacao_mensagem, recomendacao_link = gerar_recomendacao_emocional(df)

if recomendacao_link and recomendacao_mensagem:
    st.markdown(f"**{recomendacao_mensagem}**")
    st.markdown(f"[{recomendacao_link}]({recomendacao_link})")

# === VISUALIZAÇÕES ===
col1, col2 = st.columns(2)
with col1:
    st.subheader("📊 Distribuição das Suas Emoções")
    if not df.empty:
        emocao_counts = df["emocao"].value_counts().reset_index()
        emocao_counts.columns = ["emocao", "contagem"]
        fig_pie = px.pie(
            emocao_counts,
            values="contagem",
            names="emocao",
            title="Sua Paisagem Emocional",
            hole=0.3,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Nenhum dado emocional para exibir ainda.")

with col2:
    st.subheader("📈 Emoções ao Longo do Tempo")
    if not df.empty:
        fig_line = px.line(
            df,
            x="timestamp",
            y="emocao",
            title="Variação das Emoções",
            markers=True,
            line_shape="linear",
        )
        fig_line.update_layout(yaxis_title="Emoção")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Nenhum dado emocional para exibir ainda.")


# Feedback do Usuário
st.subheader("✨ Sua Opinião é Importante!")
with st.form("form_feedback"):
    feedback_emocao = st.selectbox(
        "Como você se sente sobre esta análise?",
        ["Ótimo", "Bom", "Neutro", "Ruim", "Péssimo"]
    )
    feedback_comentario = st.text_area("Comentários (opcional):")
    submitted = st.form_submit_button("Enviar Feedback")
    if submitted:
        st.success("Obrigado pelo seu feedback! Isso me ajuda a melhorar. 🚀")

# Suporte extra (CVV e outros)
st.subheader("🆘 Precisa de ajuda imediata?")
st.write(
    "Se você está passando por um momento muito difícil, por favor, não hesite em procurar apoio profissional:"
)
st.markdown("- **Centro de Valorização da Vida (CVV):** Ligue 188 ou acesse [cvv.org.br](https://www.cvv.org.br)")
st.markdown(
    "- **Busque um profissional de saúde mental:** psicólogos e psiquiatras podem te ajudar. Se for uma emergência, procure o serviço de saúde mais próximo."
)
st.info("Interaja mais comigo para que eu possa te ajudar melhor 💙")

# Autoajuda CBT guiada – Refletir sobre um pensamento difícil
with st.expander("💭 Refletir sobre um pensamento difícil"):
    pensamento = st.text_area("1. O que está te incomodando?", key="reflexao_pensamento")
    impacto = st.text_area("2. Como isso afetou seu dia?", key="reflexao_impacto")
    reframe = st.text_area("3. Uma forma mais equilibrada de pensar:", key="reflexao_reframe")

    if st.button("💾 Salvar reflexão", type="primary"):
        if pensamento.strip() and impacto.strip() and reframe.strip():
            nova_reflexao = {
                "timestamp": datetime.now().isoformat(),
                "pensamento": pensamento,
                "impacto": impacto,
                "reframe": reframe
            }

            reflexoes_anteriores = carregar_reflexoes(username) or []
            reflexoes_anteriores.append(nova_reflexao)

            sucesso = salvar_reflexoes(reflexoes_anteriores, username)
            if sucesso:
                st.success("Reflexão registrada com sucesso! 💪")
            else:
                st.error("Erro ao salvar a reflexão.")
        else:
            st.warning("Por favor, preencha todos os campos antes de salvar.")

    # Visualização das últimas reflexões
    reflexoes_existentes = carregar_reflexoes(username)
    if reflexoes_existentes:
        with st.expander("🧾 Visualizar reflexões anteriores"):
            for ref in reversed(reflexoes_existentes[-5:]):  # mostra só as 5 últimas
                st.markdown(f"""
                🗓️ **{ref['timestamp']}**
                - **Pensamento:** {ref['pensamento']}
                - **Impacto:** {ref['impacto']}
                - **Reestruturação:** {ref['reframe']}
                """)


# 📜 Histórico completo com filtros, ícones e exclusão
with st.expander("📜 Histórico completo e exportação"):
    st.subheader("📅 Filtros para análise emocional")

    col1, col2, col3 = st.columns(3)
    with col1:
        # Garante que data_inicio e data_fim tenham valores padrão razoáveis mesmo com df vazio
        min_date = df["timestamp"].min().date() if not df.empty else datetime.now().date()
        data_inicio = st.date_input("Data inicial", value=min_date)
    with col2:
        max_date = df["timestamp"].max().date() if not df.empty else datetime.now().date()
        data_fim = st.date_input("Data final", value=max_date)
    with col3:
        # Garante que as opções de filtro_emocao sejam sempre strings
        unique_emotions = df["emocao"].astype(str).unique().tolist() if "emocao" in df.columns else []
        filtro_emocao = st.selectbox("Filtrar por emoção", options=["Todas"] + sorted(unique_emotions))

    palavra_chave = st.text_input("🔍 Filtrar por palavra-chave (opcional)")

    # Aplicar filtros
    df_filtrado = df.copy()
    if not df.empty: # Aplica filtros apenas se o DataFrame não estiver vazio
        df_filtrado = df_filtrado[df_filtrado["timestamp"].dt.date.between(data_inicio, data_fim)]

        if filtro_emocao != "Todas":
            df_filtrado = df_filtrado[df_filtrado["emocao"] == filtro_emocao]

        if palavra_chave:
            df_filtrado = df_filtrado[df_filtrado["emocao"].str.contains(palavra_chave, case=False, na=False)]

    # Ícones por emoção
    emoji_cor = {
        "feliz": "🟠",
        "triste": "🔵",
        "ansioso": "🟣",
        "cansado": "🟤",
        "irritado": "🔴",
        "calmo": "🟢",
        "preocupado": "🟡",
        "grato": "🟡",
        "desesperado": "⚫",
        "suicida": "⚫",
        "animado": "🟢" # Adicionado para completar
    }

    if not df_filtrado.empty and "emocao" in df_filtrado.columns:
        df_filtrado["emoção com ícone"] = df_filtrado["emocao"].apply(lambda e: f"{emoji_cor.get(e.lower(), '⚪')} {e}")
        st.dataframe(df_filtrado[["timestamp", "emoção com ícone"]].sort_values("timestamp", ascending=False), use_container_width=True)
    else:
        st.info("Nenhum dado emocional para exibir com os filtros aplicados.")

    # Exportar CSV
    if not df_filtrado.empty:
        st.download_button(
            label="⬇️ Baixar histórico filtrado (CSV)",
            data=df_filtrado.to_csv(index=False).encode('utf-8'),
            file_name="historico_emocional.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum dado para exportar.")

    # Botão para apagar tudo
    st.markdown("---")
    if st.button("🗑️ Apagar todo o histórico emocional"):
        salvar_emocoes({}, username)
        st.success("Todos os dados emocionais foram apagados com carinho.")
        st.rerun()


# Alerta de risco real
# Acesso a 'ultima_emocao' e 'ultimos' deve ser seguro
if ultima_emocao is not None and ultima_emocao.lower() in ["desesperado", "suicida"] or ultimos.count("triste") >= 4:
    st.warning("🚨 **Alerta!** Suas emoções recentes indicam a necessidade de atenção especial. Por favor, considere procurar ajuda profissional.")
    st.markdown("- **Centro de Valorização da Vida (CVV):** Ligue **188** ou acesse [cvv.org.br](https://www.cvv.org.br)")