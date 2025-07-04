# utils.py

import streamlit as st
import os
from supabase import create_client, Client
import json
from dotenv import load_dotenv
from pathlib import Path
import re
from cryptography.fernet import Fernet

# Garante que as variáveis de ambiente do .env sejam carregadas
load_dotenv()

# --- Conexão Centralizada com o Supabase (MANTIDA COMO ESTÁ) ---
supabase: Client = None
try:
    supabase_url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
except Exception as e:
    print(f"ERRO: Falha ao conectar com Supabase: {e}")

# --- INICIALIZAÇÃO DAS CHAVES DE CRIPTOGRAFIA FERNTE ---

# Chave para criptografia de preferências (conteúdo total do arquivo preferencias_*.json)
ENCRYPTION_KEY_PREFERENCES_STR = st.secrets.get("ENCRYPTION_KEY_PREFERENCES") or os.getenv("ENCRYPTION_KEY_PREFERENCES")
fernet_preferences = None
if ENCRYPTION_KEY_PREFERENCES_STR:
    try:
        fernet_preferences = Fernet(ENCRYPTION_KEY_PREFERENCES_STR.encode())
        print("Chave Fernet 'preferencias' carregada com sucesso.")
    except Exception as e:
        print(f"ERRO: Falha ao inicializar Fernet 'preferencias': {e}")
        st.error("Erro de configuração de criptografia para preferências. Verifique ENCRYPTION_KEY_PREFERENCES.")
else:
    print("AVISO: Variável ENCRYPTION_KEY_PREFERENCES não encontrada.")

# Chave para criptografia de usuários (assinaturas.json, nomes de arquivo de chat)
ENCRYPTION_KEY_USERS_STR = st.secrets.get("ENCRYPTION_KEY_USERS") or os.getenv("ENCRYPTION_KEY_USERS")
fernet_users = None
if ENCRYPTION_KEY_USERS_STR:
    try:
        fernet_users = Fernet(ENCRYPTION_KEY_USERS_STR.encode())
        print("Chave Fernet 'usuarios' carregada com sucesso.")
    except Exception as e:
        print(f"ERRO: Falha ao inicializar Fernet 'usuarios': {e}")
        st.error("Erro de configuração de criptografia para usuários. Verifique ENCRYPTION_KEY_USERS.")
else:
    print("AVISO: Variável ENCRYPTION_KEY_USERS não encontrada.")

# Chave para criptografia geral (feedback.json, memoria_jarvis.json)
ENCRYPTION_KEY_GENERAL_STR = st.secrets.get("ENCRYPTION_KEY_GENERAL") or os.getenv("ENCRYPTION_KEY_GENERAL")
fernet_general = None
if ENCRYPTION_KEY_GENERAL_STR:
    try:
        fernet_general = Fernet(ENCRYPTION_KEY_GENERAL_STR.encode())
        print("Chave Fernet 'geral' carregada com sucesso.")
    except Exception as e:
        print(f"ERRO: Falha ao inicializar Fernet 'geral': {e}")
        st.error("Erro de configuração de criptografia geral. Verifique ENCRYPTION_KEY_GENERAL.")
else:
    print("AVISO: Variável ENCRYPTION_KEY_GENERAL não encontrada.")

# --- FUNÇÕES DE CRIPTOGRAFIA/DESCRIPTOGRAFIA (AGORA USANDO CHAVES ESPECÍFICAS) ---

# Funções para criptografia/descriptografia de STRINGS (usando a chave de usuários)
# Estas serão usadas para nomes de usuário como chaves ou valores
def encrypt_string_users(text_string):
    """Criptografa uma string usando a chave Fernet de usuários."""
    if fernet_users:
        return fernet_users.encrypt(text_string.encode()).decode()
    return text_string # Retorna original se fernet_users não estiver configurado

def decrypt_string_users(encrypted_text_string):
    """Descriptografa uma string usando a chave Fernet de usuários."""
    if fernet_users:
        try:
            return fernet_users.decrypt(encrypted_text_string.encode()).decode()
        except Exception as e:
            print(f"ERRO: Falha ao descriptografar string de usuário. Retornando original. Erro: {e}")
            return encrypted_text_string
    return encrypted_text_string

# Funções para criptografia/descriptografia de CONTEÚDO DE ARQUIVO (usando a chave geral)
# Estas serão usadas para criptografar/descriptografar JSONs inteiros
def encrypt_file_content_general(data_json_string):
    """Criptografa uma string JSON usando a chave Fernet geral."""
    if fernet_general:
        return fernet_general.encrypt(data_json_string.encode()).decode()
    return data_json_string

def decrypt_file_content_general(encrypted_data_string):
    """Descriptografa uma string criptografada usando a chave Fernet geral."""
    if fernet_general:
        try:
            return fernet_general.decrypt(encrypted_data_string.encode()).decode()
        except Exception as e:
            print(f"ERRO: Falha ao descriptografar conteúdo de arquivo geral. Retornando original. Erro: {e}")
            return encrypted_data_string
    return encrypted_data_string


# --- Função de Normalização de Chaves (para nomes de tópicos em preferencias_*.json) ---
# Usada para garantir consistência em como chaves são armazenadas/acessadas
def normalize_preference_key(key_string):
    """Normaliza uma string de chave para um formato consistente (minúsculas, underscores, sem caracteres especiais)."""
    if not isinstance(key_string, str):
        return str(key_string).strip().lower()
    normalized_key = key_string.strip().lower()
    normalized_key = re.sub(r'\s+', '_', normalized_key)
    normalized_key = re.sub(r'[^a-z0-9_]', '', normalized_key)
    return normalized_key


# --- FUNÇÕES carregar_preferencias e salvar_preferencias (MUDANÇAS PARA FERNTE) ---
# Lidam com preferencias_USUARIO.json - Criptografia TOTAL do arquivo.
def carregar_preferencias(username):
    """
    Carrega as preferências do Supabase (se conectado) ou do arquivo JSON local como fallback.
    Descriptografa o conteúdo inteiro do arquivo usando Fernet (chave de preferências).
    Normaliza as chaves internas do JSON.
    """
    data_loaded_raw = {}

    # 1. Tentar carregar do Supabase
    if supabase:
        try:
            response = supabase.table('preferencias').select('data_preferences').eq('username', username).execute()
            if response.data and response.data[0]['data_preferences']:
                print(f"Preferências de '{username}' carregadas do Supabase.")
                data_from_supabase = response.data[0]['data_preferences']
                
                if isinstance(data_from_supabase, str): # Assumimos que Supabase armazena como string criptografada
                    decrypted_data_str = decrypt_file_content_general(data_from_supabase) # Usa a chave geral para preferencias também
                    try:
                        data_loaded_raw = json.loads(decrypted_data_str)
                    except json.JSONDecodeError:
                        print("AVISO: Dados do Supabase não são JSON válido após descriptografia. Tentando como JSON bruto.")
                        try:
                            data_loaded_raw = json.loads(data_from_supabase) # Tenta como JSON não criptografado
                        except json.JSONDecodeError:
                            print("AVISO: Dados do Supabase não são JSON válido. Retornando vazio.")
                            return {}
                elif isinstance(data_from_supabase, dict): # Caso o Supabase armazene como JSON direto (não criptografado no banco)
                    data_loaded_raw = data_from_supabase
        except Exception as e:
            print(f"Erro ao carregar do Supabase, tentando arquivo local. Erro: {e}")
    
    # 2. Fallback para o arquivo local
    if not data_loaded_raw:
        print(f"Conexão com Supabase não disponível ou sem dados. Carregando preferências locais para '{username}'.")
        caminho_arquivo = f"dados/preferencias_{username}.json"
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                encrypted_file_content = f.read()
                decrypted_file_content = decrypt_file_content_general(encrypted_file_content) # Usa a chave geral
                try:
                    data_loaded_raw = json.loads(decrypted_file_content)
                except json.JSONDecodeError:
                    print("AVISO: Conteúdo do arquivo local não é JSON válido após descriptografia. Verificando dados originais.")
                    try:
                        data_loaded_raw = json.loads(encrypted_file_content) # Tenta como JSON não criptografado
                    except json.JSONDecodeError:
                        print("ERRO FATAL: Conteúdo do arquivo local não é JSON válido (criptografado ou não). Retornando vazio.")
                        return {}
        else:
            return {} 

    # Normalização das chaves internas do JSON (mantida)
    normalized_preferences = {}
    for topico, valor in data_loaded_raw.items():
        normalized_preferences[normalize_preference_key(topico)] = valor
    
    return normalized_preferences

def salvar_preferencias(data, username):
    """
    Salva as preferências no Supabase (se conectado) e também no arquivo JSON local como backup.
    Criptografa o conteúdo inteiro do arquivo usando Fernet (chave de preferências).
    Normaliza as chaves internas do JSON.
    """
    # Normalização das chaves internas
    data_to_save_normalized_keys = {}
    for topico, valor in data.items():
        data_to_save_normalized_keys[normalize_preference_key(topico)] = valor

    # Converte o dicionário normalizado para string JSON
    data_json_string = json.dumps(data_to_save_normalized_keys, ensure_ascii=False)

    # CRIPTOGRAFA a string JSON inteira
    encrypted_data_string = encrypt_file_content_general(data_json_string) # Usa a chave geral para preferencias também

    # Salvar no Supabase
    if supabase:
        try:
            supabase.table('preferencias').upsert({
                "username": username,
                "data_preferences": encrypted_data_string # Salva a STRING CRIPTOGRAFADA
            }).execute()
            print(f"Preferências de '{username}' salvas no Supabase (criptografadas).")
        except Exception as e:
            print(f"Erro ao salvar no Supabase (mesmo com criptografia de preferências): {e}")
    
    # Backup local
    caminho_arquivo = f"dados/preferencias_{username}.json"
    try:
        Path(caminho_arquivo).parent.mkdir(parents=True, exist_ok=True)
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(encrypted_data_string) # Escreve a STRING CRIPTOGRAFADA
        print(f"Preferências de '{username}' salvas localmente (criptografadas).")
    except Exception as e:
        print(f"Erro ao salvar preferências localmente: {e}")