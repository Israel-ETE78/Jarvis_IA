import streamlit as st
import json # Não é mais necessário para carregar/salvar assinaturas diretamente
import bcrypt
import os
from datetime import datetime
from dotenv import load_dotenv

# Importa as funções do seu novo módulo assinaturas_manager.py
from assinaturas_manager import carregar_assinaturas, adicionar_assinatura, remover_assinatura # Importe o que você precisar

# Carrega as variáveis do arquivo .env para este módulo
load_dotenv()

# --- Funções Auxiliares (A FUNÇÃO carregar_assinaturas() ABAIXO SERÁ REMOVIDA) ---
# A função carregar_assinaturas() que lia diretamente o JSON será substituída
# pela que vem de assinaturas_manager.py.
# Esta função local não é mais necessária:
# def carregar_assinaturas():
#     """Carrega os dados de assinaturas do arquivo JSON."""
#     caminho_arquivo = "dados/assinaturas.json"
#     if os.path.exists(caminho_arquivo):
#         with open(caminho_arquivo, 'r', encoding='utf-8') as f:
#             try:
#                 data = json.load(f)
#                 return data if isinstance(data, dict) else {}
#             except json.JSONDecodeError:
#                 return {}
#     return {}


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
            # AGORA USAMOS A FUNÇÃO carregar_assinaturas() DO assinaturas_manager.py
            # Essa função já lida com a descriptografia das chaves de usuário (nomes de usuário)
            # e, se configurado, dos valores internos.
            assinaturas = carregar_assinaturas() 
            
            # O 'username' digitado pelo usuário deve corresponder a uma chave NOVO_FORMATO_TEXTO_CLARO
            # no dicionário retornado por carregar_assinaturas()
            user_data = assinaturas.get(username)

            if user_data:
                # O campo 'senha' no user_data já estará no formato hash (bcrypt)
                # pois não foi criptografado com Fernet.
                hash_salvo = user_data.get('senha', '').encode('utf-8')
                senha_digitada_bytes = password.encode('utf-8')
                
                if bcrypt.checkpw(senha_digitada_bytes, hash_salvo):
                    try:
                        # Certifique-se de que 'expiracao' é uma string no formato correto
                        # e que não foi criptografada, ou que _decrypt_signature_value a converteu de volta para string
                        expiracao = datetime.strptime(user_data['expiracao'], "%Y-%m-%d %H:%M:%S")
                    except (KeyError, ValueError) as e:
                        st.error(f"Erro no formato de expiração do usuário. Contacte o suporte. Erro: {e}")
                        print(f"DEBUG: user_data['expiracao'] = {user_data.get('expiracao')}")
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
            
            st.error("Usuário ou senha inválidos.")
            return False
            
    return False