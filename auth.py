import streamlit as st
import json # Agora é necessário novamente para carregar o JSON diretamente
import bcrypt
import os
from datetime import datetime
from dotenv import load_dotenv

# Não há mais importação de assinaturas_manager.py aqui!
# from assinaturas_manager import carregar_assinaturas, adicionar_assinatura, remover_assinatura 

# Carrega as variáveis do arquivo .env para este módulo
load_dotenv()

# --- Funções Auxiliares (AGORA carregar_assinaturas() É RECOLOCADA AQUI) ---
def carregar_assinaturas():
    """Carrega os dados de assinaturas do arquivo JSON em texto claro."""
    caminho_arquivo = "dados/assinaturas.json"
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                # Se o arquivo não for um JSON válido (ex: criptografado acidentalmente)
                print(f"ERRO: O arquivo '{caminho_arquivo}' não é um JSON válido. Retornando vazio.")
                return {}
    print(f"AVISO: Arquivo '{caminho_arquivo}' não encontrado. Retornando assinaturas vazias.")
    return {}

# --- Lógica Principal de Autenticação ---
def check_password():
    """Exibe o formulário de login e verifica as credenciais do admin ou de assinantes."""
    
    if st.session_state.get("logged_in"):
        return True

    st.title("Login - Jarvis IA")
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            # --- VERIFICAÇÃO PRIORITÁRIA DE ADMINISTRADOR ---
            ADMIN_USER = st.secrets.get("ADMIN_USERNAME") or os.getenv("ADMIN_USERNAME")
            ADMIN_PASS = st.secrets.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")

            if username == ADMIN_USER and password == ADMIN_PASS:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success("Acesso de administrador concedido!")
                st.rerun()
                return True
            
            # --- LÓGICA PARA USUÁRIOS NORMAIS (ASSINANTES) ---
            assinaturas = carregar_assinaturas() # Agora usa a função local neste auth.py
            
            user_data = assinaturas.get(username)

            if user_data:
                hash_salvo = user_data.get('senha', '').encode('utf-8')
                senha_digitada_bytes = password.encode('utf-8')
                
                if bcrypt.checkpw(senha_digitada_bytes, hash_salvo):
                    try:
                        expiracao = datetime.strptime(user_data['expiracao'], "%Y-%m-%d %H:%M:%S")
                    except (KeyError, ValueError) as e:
                        st.error(f"Erro no formato da data de expiração do usuário. Contacte o suporte técnico. (Detalhes: {e})")
                        print(f"DEBUG: user_data['expiracao'] = {user_data.get('expiracao')}, Tipo: {type(user_data.get('expiracao'))}")
                        return False

                    if datetime.now() < expiracao:
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = username
                        st.success("Login bem-sucedido!")
                        st.rerun()
                        return True
                    else:
                        st.error("❌ Sua assinatura expirou.")
                        return False
                else: # Senha incorreta
                    st.error("Usuário ou senha inválidos.")
                    return False
            else: # Usuário não encontrado
                st.error("Usuário ou senha inválidos.")
                return False
            
    return False