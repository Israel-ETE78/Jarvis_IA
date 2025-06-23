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
            # Pega o dicionário de usuários dos Secrets.
            users_credentials = st.secrets.get("users", {})
            
            # Verifica se o usuário digitado existe e se a senha corresponde
            if username_input in users_credentials and users_credentials[username_input] == password_input:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username_input 
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    
    return False