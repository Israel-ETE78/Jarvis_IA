# auth_admin_pages.py
import streamlit as st
from auth import check_password # Import your existing check_password function

ADMIN_USERNAME = "israel" # Define the admin username here. Make sure it matches the one in app.py

def require_admin_access():
    """
    Ensures that only the specified ADMIN_USERNAME can access the page.
    If not authenticated or not the admin, it stops the page execution.
    """
    # First, ensure general authentication has occurred.
    # This will display the login form if the user is not logged in.
    if not check_password():
        st.stop() # Stop execution if user is not authenticated (auth.py handles the login UI)

    # Now, check if the authenticated user has the necessary admin privilege.
    if st.session_state.get("username") != ADMIN_USERNAME:
        st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
        st.info("Por favor, faça login com uma conta de administrador para acessar esta seção.")
        st.stop() # Stop execution if the user is authenticated but not the admin