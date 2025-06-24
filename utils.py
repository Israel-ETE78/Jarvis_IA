import json
import streamlit as st

# Coloque estas funções aqui
def carregar_preferencias(username):
    """Carrega as preferências de um usuário específico."""
    filename = f"preferencias_{username}.json"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def salvar_preferencias(preferencias, username):
    """Salva as preferências de um usuário específico."""
    filename = f"preferencias_{username}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(preferencias, f, ensure_ascii=False, indent=4)