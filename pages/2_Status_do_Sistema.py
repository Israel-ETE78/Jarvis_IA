# pages/2_Status_do_Sistema.py

import streamlit as st
import os
import datetime # Importado uma vez aqui, usado como datetime.datetime
import requests
import json
import subprocess
import time
import sys
from dotenv import load_dotenv
from utils import carregar_chats # Mantido, e usado para carregar chats do GitHub

# Removendo importação duplicada de streamlit
# import streamlit as st 
from auth_admin_pages import require_admin_access # Import the new function

# === IMPORTANT: Apply the admin access check at the very beginning ===
require_admin_access()

# --- Botão de voltar para o chat principal ---
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.switch_page("app.py")

st.title("Painel de Diagnóstico do Jarvis")
st.write("Informações de diagnóstico exclusivas para administradores.")

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
col1, col2, col3 = st.columns(3) # Mantém as 3 colunas para o layout

with col1:
    num_memorias = contar_entradas_json("memoria_jarvis.json", 'dict_de_listas')
    st.metric(label="Memórias de Longo Prazo", value=f"{num_memorias} Itens")

with col2:
    username = st.session_state.get("username", "default")
    preferencias_path = f"preferencias_{username}.json"
    num_prefs = contar_entradas_json(preferencias_path, 'dict')
    st.metric(label="Preferências do Usuário", value=f"{num_prefs} Itens")

# --- INÍCIO DA CORREÇÃO PARA O HISTÓRICO DE CHATS ---
with col3:
    username = st.session_state.get("username") # Obtém o nome de usuário logado

    quantidade_chats_display = "0 Itens"
    ultima_vez_salvo_display = "N/A"

    if username: # Carrega apenas se houver um usuário logado
        with st.spinner(f"Carregando histórico de chats de {username} do GitHub..."):
            user_chats = carregar_chats(username) # Usa a função que carrega do GitHub

        if user_chats:
            total_chats_usuario = len(user_chats)
            quantidade_chats_display = f"{total_chats_usuario} Chats"

            all_timestamps = []
            for chat_id, chat_data in user_chats.items():
                if isinstance(chat_data, dict) and "messages" in chat_data and chat_data["messages"]:
                    last_message = chat_data["messages"][-1]
                    if "timestamp" in last_message:
                        try:
                            all_timestamps.append(datetime.datetime.fromisoformat(last_message["timestamp"]))
                        except ValueError:
                            pass # Ignora timestamps inválidos
            
            if all_timestamps:
                latest_chat_time = max(all_timestamps)
                ultima_vez_salvo_display = latest_chat_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                ultima_vez_salvo_display = "N/A (Nenhum timestamp válido encontrado)"
        else:
            quantidade_chats_display = "0 Chats (usuário)"
            ultima_vez_salvo_display = "N/A"
    else:
        quantidade_chats_display = "Usuário não logado"
        ultima_vez_salvo_display = "N/A"
    
    st.metric(label="Tamanho do Histórico de Chats", value=quantidade_chats_display, delta=f"Última vez salvo: {ultima_vez_salvo_display}")
# --- FIM DA CORREÇÃO PARA O HISTÓRICO DE CHATS ---


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
                script_path = os.path.join(RAIZ_PROJETO, "treinar_memoria.py")
                resultado = subprocess.run(
                    [sys.executable, script_path],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True,
                    check=True,
                    encoding='utf-8',
                    errors='ignore',
                    cwd=RAIZ_PROJETO
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
                    st.code(e.stdout)
            except FileNotFoundError:
                st.error("Não foi possível encontrar o script 'treinar_memoria.py'. Verifique o caminho.")


st.header("Log de Atividades Recentes")
with st.expander("Ver últimas 15 entradas do log"):
    log_content = ler_logs("jarvis_log.txt")
    st.code(log_content, language='log')