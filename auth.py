# auth.py

import streamlit as st
import json
import bcrypt
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Funções Auxiliares (carregar_assinaturas E salvar_assinaturas) ---
def carregar_assinaturas(): #
    """Carrega os dados de assinaturas do arquivo JSON em texto claro.""" #
    caminho_arquivo = "dados/assinaturas.json" #
    if os.path.exists(caminho_arquivo): #
        with open(caminho_arquivo, 'r', encoding='utf-8') as f: #
            try: #
                data = json.load(f) #
                return data if isinstance(data, dict) else {} #
            except json.JSONDecodeError: #
                print(f"ERRO: O arquivo '{caminho_arquivo}' não é um JSON válido. Retornando vazio.") #
                return {} #
    print(f"AVISO: Arquivo '{caminho_arquivo}' não encontrado. Retornando assinaturas vazias.") #
    return {} #

def salvar_assinaturas(assinaturas_data): #
    """Salva os dados de assinaturas no arquivo JSON em texto claro.""" #
    caminho_arquivo = "dados/assinaturas.json" #
    os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True) #
    with open(caminho_arquivo, 'w', encoding='utf-8') as f: #
        json.dump(assinaturas_data, f, ensure_ascii=False, indent=4) #
    print(f"Assinaturas salvas em '{caminho_arquivo}'.") #


def handle_password_change(): #
    """Exibe o formulário de alteração de senha forçada para o primeiro login.""" #
    st.title(f"Olá, {st.session_state.get('username')}! Por favor, altere sua senha.") #
    st.info("Esta é uma medida de segurança para o seu primeiro acesso.") #

    with st.form("change_password_form"): #
        new_password = st.text_input("Nova Senha", type="password") #
        confirm_password = st.text_input("Confirmar Nova Senha", type="password") #
        change_submitted = st.form_submit_button("Alterar Senha") #

        if change_submitted: #
            if new_password and new_password == confirm_password: #
                if len(new_password) < 6: # Exemplo de validação mínima
                    st.error("A nova senha deve ter pelo menos 6 caracteres.") #
                    return False #

                assinaturas = carregar_assinaturas() #
                username = st.session_state.get("username") #
                
                if username in assinaturas: #
                    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8') #
                    assinaturas[username]['senha'] = hashed_password #
                    assinaturas[username]['primeiro_login'] = False # Marca como senha alterada

                    salvar_assinaturas(assinaturas) # Salva as alterações
                    
                    st.session_state["must_change_password"] = False #
                    st.session_state["logged_in"] = True # Confirma o login após a alteração
                    st.success("Senha alterada com sucesso! Você já pode acessar o aplicativo.") #
                    st.rerun() #
                    return True #
                else: #
                    st.error("Erro: Usuário não encontrado no sistema de assinaturas.") #
                    return False #
            elif not new_password: #
                st.error("A nova senha não pode ser vazia.") #
            else: #
                st.error("As senhas não coincidem.") #
        
    return False # Continua exibindo o formulário de alteração de senha até ser bem-sucedido


# --- Lógica Principal de Autenticação ---
def check_password(): #
    """Exibe o formulário de login e verifica as credenciais do admin ou de assinantes.""" #
    
    # Se o usuário já está logado E não precisa alterar a senha, permite o acesso direto.
    if st.session_state.get("logged_in") and not st.session_state.get("must_change_password", False): #
        return True #

    # Se o usuário precisa alterar a senha (foi redirecionado para cá), mostra o formulário de alteração.
    if st.session_state.get("must_change_password", False): #
        return handle_password_change() #

    st.title("Login - Jarvis IA") #
    with st.form("login_form"): #
        username = st.text_input("Usuário", key="login_username_input") #
        password = st.text_input("Senha", type="password", key="login_password_input") #
        submitted = st.form_submit_button("Entrar") #

        if submitted: #
            # --- VERIFICAÇÃO PRIORITÁRIA DE ADMINISTRADOR ---
            ADMIN_USER = st.secrets.get("ADMIN_USERNAME") or os.getenv("ADMIN_USERNAME") #
            ADMIN_PASS = st.secrets.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD") #

            if username == ADMIN_USER and password == ADMIN_PASS: #
                st.session_state["logged_in"] = True #
                st.session_state["username"] = username #
                st.session_state["must_change_password"] = False # Admin não precisa alterar senha inicial
                st.success("Acesso de administrador concedido!") #
                st.rerun() #
                return True #
            
            # --- LÓGICA PARA USUÁRIOS NORMAIS (ASSINANTES) ---
            assinaturas = carregar_assinaturas() #
            
            user_data = assinaturas.get(username) #

            if user_data: #
                hash_salvo = user_data.get('senha', '').encode('utf-8') #
                senha_digitada_bytes = password.encode('utf-8') #
                
                if bcrypt.checkpw(senha_digitada_bytes, hash_salvo): #
                    try: #
                        expiracao = datetime.strptime(user_data['expiracao'], "%Y-%m-%d %H:%M:%S") #
                    except (KeyError, ValueError) as e: #
                        st.error(f"Erro no formato da data de expiração do usuário. Contacte o suporte técnico. (Detalhes: {e})") #
                        print(f"DEBUG: user_data['expiracao'] = {user_data.get('expiracao')}, Tipo: {type(user_data.get('expiracao'))}") #
                        return False #

                    if datetime.now() < expiracao: #
                        # Login bem-sucedido, agora verifica se é o primeiro login
                        if user_data.get("primeiro_login", False): # Assume false se o campo não existe
                            st.session_state["logged_in"] = True # Login temporariamente concedido para ir para a tela de mudança de senha
                            st.session_state["username"] = username #
                            st.session_state["must_change_password"] = True # Sinaliza para alterar a senha
                            st.warning("É seu primeiro login. Por favor, altere sua senha.") #
                            st.rerun() # Redireciona para a função handle_password_change
                            return False # Não retorna True ainda, pois não está "totalmente" logado
                        else: #
                            st.session_state["logged_in"] = True #
                            st.session_state["username"] = username #
                            st.session_state["must_change_password"] = False #
                            st.success("Login bem-sucedido!") #
                            st.rerun() #
                            return True #
                    else: #
                        st.error("❌ Sua assinatura expirou.") #
                        return False #
                else: # Senha incorreta
                    st.error("Usuário ou senha inválidos.") #
                    return False #
            else: # Usuário não encontrado
                st.error("Usuário ou senha inválidos.") #
                return False #
            
    return False # Retorna False se o login ainda não foi efetuado ou falhou