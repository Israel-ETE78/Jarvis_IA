# utils.py

import streamlit as st
import os
from supabase import create_client, Client
import json
from dotenv import load_dotenv
from pathlib import Path

# Garante que as variáveis de ambiente do .env sejam carregadas
load_dotenv()

# --- Conexão Centralizada com o Supabase ---
supabase: Client = None
try:
    supabase_url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
except Exception as e:
    print(f"ERRO: Falha ao conectar com Supabase: {e}")

def carregar_preferencias(username):
    """
    Carrega as preferências do Supabase (se conectado) ou do arquivo JSON local como fallback.
    """
    if supabase:
        try:
            response = supabase.table('preferencias').select('data_preferences').eq('username', username).execute()
            if response.data:
                print(f"Preferências de '{username}' carregadas do Supabase.")
                return response.data[0]['data_preferences']
        except Exception as e:
            print(f"Erro ao carregar do Supabase, tentando arquivo local. Erro: {e}")
    
    # Fallback para o arquivo local
    print(f"Conexão com Supabase não disponível. Carregando preferências locais para '{username}'.")
    caminho_arquivo = f"dados/preferencias_{username}.json"
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_preferencias(data, username):
    """
    Salva as preferências no Supabase (se conectado) e também no arquivo JSON local como backup.
    """
    # Salva na nuvem primeiro, se possível
    if supabase:
        try:
            supabase.table('preferencias').upsert({
                "username": username,
                "data_preferences": data
            }).execute()
            print(f"Preferências de '{username}' salvas no Supabase.")
        except Exception as e:
            print(f"Erro ao salvar no Supabase: {e}")
    
    # Salva/atualiza o arquivo local independentemente
    caminho_arquivo = f"dados/preferencias_{username}.json"
    try:
        Path(caminho_arquivo).parent.mkdir(parents=True, exist_ok=True)
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Preferências de '{username}' salvas localmente.")
    except Exception as e:
        print(f"Erro ao salvar preferências localmente: {e}")