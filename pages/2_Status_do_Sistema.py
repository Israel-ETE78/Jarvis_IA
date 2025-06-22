# pages/2_Status_do_Sistema.py

import streamlit as st
import os
import datetime
import requests
import json
import subprocess
import time
from dotenv import load_dotenv

# --- CAMINHO ROBUSTO PARA A RAIZ DO PROJETO ---
# Isso garante que sempre encontraremos os arquivos na pasta principal
# __file__ se refere a este arquivo atual (2_Status_do_Sistema.py)
# os.path.dirname() pega o diretório dele (a pasta 'pages')
# os.path.join(..., "..") "sobe" um nível para a pasta 'Jarvis_IA'
RAIZ_PROJETO = os.path.join(os.path.dirname(__file__), "..")

# --- CARREGAR AS VARIÁVEIS DE AMBIENTE ---
load_dotenv(dotenv_path=os.path.join(RAIZ_PROJETO, ".env"))

st.set_page_config(page_title="Status do Sistema - Jarvis", layout="wide")
st.title("🩺 Painel de Diagnóstico do Jarvis")
st.write("Monitoramento da saúde e dos componentes do sistema em tempo real.")

# --- Funções de Verificação ---

@st.cache_data(ttl=300)
def verificar_status_api(url, headers={}):
    """Checks the status of an API by making a simple request."""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code in [200, 401]: # 200 (OK) or 401 (OK, but needs key) indicate the service is online
            return "✅ Operacional", "green"
        else:
            return f"❌ Erro {response.status_code}", "red"
    except requests.exceptions.RequestException:
        return "❌ Offline", "red"

def get_metadados_arquivo(filename):
    """Returns the size and modification date of a file in the project root."""
    filepath = os.path.join(RAIZ_PROJETO, filename)
    try:
        if os.path.exists(filepath):
            tamanho = os.path.getsize(filepath)
            data_mod = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            return f"{tamanho/1024:.2f} KB", data_mod.strftime("%d/%m/%Y %H:%M:%S")
        else:
            return "Não encontrado", "N/A"
    except Exception:
        return "Erro ao ler", "N/A"

def contar_entradas_json(filename, tipo='dict_de_listas'):
    """Counts entries in different types of JSON files in the project root."""
    filepath = os.path.join(RAIZ_PROJETO, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if tipo == 'dict_de_listas':
            return sum(len(items) for items in data.values())
        elif tipo == 'dict':
            return len(data)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0

def ler_logs(filename, num_linhas=15):
    """Reads the last N lines of a log file in the project root."""
    filepath = os.path.join(RAIZ_PROJETO, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
            return "".join(linhas[-num_linhas:])
    except FileNotFoundError:
        return "Arquivo de log não encontrado."

# --- Layout do Painel ---

st.header("Componentes Online")
# Changed to one column since Serper API status is removed
col1, = st.columns(1) # Using a comma to unpack a single-element tuple
with col1:
    headers_openai = {'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'}
    openai_status, openai_color = verificar_status_api("https://api.openai.com/v1/models", headers=headers_openai)
    st.metric(label="Status API OpenAI", value=openai_status)

# The Serper API status display has been removed from this section

st.header("Memória e Conhecimento")
col1, col2, col3 = st.columns(3)
with col1:
    num_memorias = contar_entradas_json("memoria_jarvis.json", 'dict_de_listas')
    st.metric(label="Memórias de Longo Prazo", value=f"{num_memorias} Itens")

with col2:
    username = st.session_state.get("username", "default")
    preferencias_path = f"preferencias_{username}.json"
    num_prefs = contar_entradas_json(preferencias_path, 'dict')
    st.metric(label="Preferências do Usuário", value=f"{num_prefs} Itens")

with col3:
    tamanho_chats, data_chats = get_metadados_arquivo("chats_historico.json")
    st.metric(label="Tamanho do Histórico de Chats", value=tamanho_chats, delta=f"Última vez salvo: {data_chats}")

st.divider()

st.header("Cérebro Local (Modelo de IA)")
col1, col2 = st.columns(2)
with col1:
    tamanho_vetores, data_treino = get_metadados_arquivo("vetores_perguntas_v2.npy")
    st.metric(label="Último Treinamento", value=data_treino, delta=f"Tamanho do arquivo de vetores: {tamanho_vetores}")

with col2:
    st.write("Forçar Retreinamento do Cérebro Local")
    if st.button("🧠 Iniciar Treinamento Agora"):
        with st.spinner("Executando o script `treinar_memoria.py`... Por favor, aguarde."):
            try:
                # Uses the absolute path to the script
                script_path = os.path.join(RAIZ_PROJETO, "treinar_memoria.py")
                resultado = subprocess.run(
                    ["python", script_path],
                    capture_output=True, text=True, check=True, encoding='utf-8', cwd=RAIZ_PROJETO
                )
                st.success("Cérebro local retreinado com sucesso!")
                with st.expander("Ver output do treinamento"):
                    st.code(resultado.stdout)
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()

            except subprocess.CalledProcessError as e:
                st.error("Ocorreu um erro ao treinar o cérebro.")
                with st.expander("Ver detalhes do erro"):
                    st.code(e.stderr)
            except FileNotFoundError:
                st.error("Não foi possível encontrar o script 'treinar_memoria.py'. Verifique o caminho.")


st.header("Log de Atividades Recentes")
with st.expander("Ver últimas 15 entradas do log"):
    log_content = ler_logs("jarvis_log.txt")
    st.code(log_content, language='log')
