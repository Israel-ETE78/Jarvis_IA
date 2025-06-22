# auth.py

import streamlit as st

def check_password():
    """Retorna True se o usuário estiver autenticado, senão exibe um formulário de senha."""
    if st.session_state.get("authenticated", False):
        return True

    st.title("🔒 Acesso Restrito - Jarvis IA")
    st.write("Por favor, insira suas credenciais para continuar.")

    with st.form("login_form"):
        username_input = st.text_input("Usuário", key="login_username")
        password_input = st.text_input("Senha", type="password", key="login_password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            correct_username = st.secrets.get("APP_USERNAME", "")
            correct_password = st.secrets.get("APP_PASSWORD", "")

            if username_input == correct_username and password_input == correct_password:
                st.session_state["authenticated"] = True
                # NOVO: Guarda o nome do usuário na sessão após o login
                st.session_state["username"] = username_input 
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    
    return False