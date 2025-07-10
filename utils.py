# utils.py

import streamlit as st
import os
from supabase import create_client, Client
import json
from dotenv import load_dotenv
from pathlib import Path
import re
from cryptography.fernet import Fernet
from github import Github, UnknownObjectException
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

def decrypt_file_content_general(encrypted_data_string):
    """Descriptografa uma string criptografada usando a chave Fernet geral."""
    if fernet_general:
        try:
            return fernet_general.decrypt(encrypted_data_string.encode()).decode()
        except Exception as e:
            print(f"ERRO: Falha ao descriptografar conteúdo de arquivo geral. Retornando original. Erro: {e}")
            return encrypted_data_string
    return encrypted_data_string

@st.cache_data(ttl=300) # Cache para otimizar leituras repetidas
def carregar_dados_do_github(caminho_arquivo):
    """Carrega o conteúdo de um arquivo do repositório do GitHub."""
    try:
        github_token = st.secrets["GITHUB_TOKEN"]
        repo_nome = st.secrets["GITHUB_REPO"]

        g = Github(github_token)
        repo = g.get_repo(repo_nome)

        arquivo = repo.get_contents(caminho_arquivo)
        conteudo_decodificado = arquivo.decoded_content.decode("utf-8")
        return conteudo_decodificado
    except UnknownObjectException:
        # Normal se o arquivo não existe (ex: novo usuário)
        return None
    except Exception as e:
        st.error(f"Erro ao carregar do GitHub ({caminho_arquivo}): {e}")
        return None

def salvar_dados_no_github(caminho_arquivo, conteudo, mensagem_commit):
    """Cria ou atualiza um arquivo no repositório do GitHub."""
    try:
        github_token = st.secrets["GITHUB_TOKEN"]
        repo_nome = st.secrets["GITHUB_REPO"]

        g = Github(github_token)
        repo = g.get_repo(repo_nome)

        try:
            arquivo_existente = repo.get_contents(caminho_arquivo)
            repo.update_file(
                path=caminho_arquivo,
                message=mensagem_commit,
                content=conteudo,
                sha=arquivo_existente.sha
            )
        except UnknownObjectException:
            repo.create_file(
                path=caminho_arquivo,
                message=mensagem_commit,
                content=conteudo
            )
        
        carregar_dados_do_github.clear() # Limpa o cache para garantir leitura fresca
        return True

    except Exception as e:
        st.error(f"Erro ao salvar no GitHub: {e}")
        return False

def excluir_arquivo_do_github(caminho_arquivo, mensagem_commit):
    """Exclui um arquivo do repositório do GitHub."""
    try:
        github_token = st.secrets["GITHUB_TOKEN"]
        repo_nome = st.secrets["GITHUB_REPO"]

        g = Github(github_token)
        repo = g.get_repo(repo_nome)
        
        arquivo = repo.get_contents(caminho_arquivo)
        repo.delete_file(
            path=arquivo.path,
            message=mensagem_commit,
            sha=arquivo.sha
        )
        carregar_dados_do_github.clear()
        return True
    except UnknownObjectException:
        return True # Sucesso se o arquivo já não existe
    except Exception as e:
        st.error(f"Erro ao excluir do GitHub: {e}")
        return False

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
# Substitua sua função carregar_preferencias por esta:

def carregar_preferencias(username):
    """
    Carrega as preferências do Supabase (se conectado) ou do GitHub como fallback.
    Descriptografa o conteúdo e normaliza as chaves.
    """
    data_loaded_raw = {}

    # 1. Tentar carregar do Supabase (lógica mantida)
    if supabase:
        try:
            response = supabase.table('preferencias').select('data_preferences').eq('username', username).execute()
            if response.data and response.data[0]['data_preferences']:
                print(f"Preferências de '{username}' carregadas do Supabase.")
                data_from_supabase = response.data[0]['data_preferences']
                
                # ... (a lógica interna de descriptografia do Supabase permanece a mesma) ...
                if isinstance(data_from_supabase, str):
                    decrypted_data_str = decrypt_file_content_general(data_from_supabase)
                    try:
                        data_loaded_raw = json.loads(decrypted_data_str)
                    except json.JSONDecodeError:
                        data_loaded_raw = json.loads(data_from_supabase)
                elif isinstance(data_from_supabase, dict):
                    data_loaded_raw = data_from_supabase
        except Exception as e:
            print(f"Erro ao carregar do Supabase, tentando fallback do GitHub. Erro: {e}")
    
    # 2. MODIFICADO: Fallback para o GitHub
    if not data_loaded_raw:
        print(f"Supabase indisponível ou sem dados. Carregando preferências do GitHub para '{username}'.")
        caminho_arquivo = f"preferencias/prefs_{username}.json"  # Recomendo usar uma pasta 'preferencias' no GitHub
        
        encrypted_file_content = carregar_dados_do_github(caminho_arquivo)
        
        if encrypted_file_content:
            decrypted_file_content = decrypt_file_content_general(encrypted_file_content)
            try:
                data_loaded_raw = json.loads(decrypted_file_content)
            except json.JSONDecodeError:
                print("AVISO: Conteúdo do GitHub não é JSON válido após descriptografia.")
                return {}
        else:
            return {} # Retorna vazio se não houver preferências em lugar nenhum

    # Normalização das chaves internas do JSON (lógica mantida)
    normalized_preferences = {normalize_preference_key(k): v for k, v in data_loaded_raw.items()}
    return normalized_preferences

# Substitua sua função salvar_preferencias por esta:

def salvar_preferencias(data, username):
    """
    Salva as preferências no Supabase (se conectado) e também no GitHub como backup.
    Criptografa o conteúdo inteiro e normaliza as chaves.
    """
    # Normalização e criptografia (lógica mantida)
    data_to_save_normalized_keys = {normalize_preference_key(k): v for k, v in data.items()}
    data_json_string = json.dumps(data_to_save_normalized_keys, ensure_ascii=False)
    encrypted_data_string = encrypt_file_content_general(data_json_string)

    # 1. Salvar no Supabase (lógica mantida)
    if supabase:
        try:
            supabase.table('preferencias').upsert({
                "username": username,
                "data_preferences": encrypted_data_string
            }).execute()
            print(f"Preferências de '{username}' salvas no Supabase.")
        except Exception as e:
            print(f"Erro ao salvar no Supabase: {e}")
    
    # 2. MODIFICADO: Backup no GitHub
    caminho_arquivo = f"preferencias/prefs_{username}.json"
    mensagem_commit = f"Atualiza preferencias do usuario {username}"
    try:
        salvar_dados_no_github(caminho_arquivo, encrypted_data_string, mensagem_commit)
        print(f"Preferências de '{username}' salvas no GitHub.")
    except Exception as e:
        print(f"Erro ao salvar preferências no GitHub: {e}")
        


def carregar_lembretes(username):
    """Carrega os lembretes de um usuário do GitHub, descriptografando o conteúdo."""
    if not username:
        return [] # Retorna uma lista vazia se não houver usuário

    caminho_arquivo = f"dados/lembretes/lembretes_{username}.json"
    
    encrypted_content = carregar_dados_do_github(caminho_arquivo)

    if encrypted_content:
        try:
            decrypted_content = decrypt_file_content_general(encrypted_content)
            return json.loads(decrypted_content)
        except Exception as e:
            print(f"AVISO: Falha ao descriptografar lembretes de '{username}'. Erro: {e}")
            # Tenta ler como JSON bruto como fallback
            try:
                return json.loads(encrypted_content)
            except json.JSONDecodeError:
                print(f"ERRO: Conteúdo de lembretes de '{username}' não é JSON válido.")
                return []
    
    return [] # Retorna lista vazia se o arquivo não existir

def salvar_lembretes(username, lembretes_data):
    """Salva a lista de lembretes do usuário no GitHub de forma criptografada."""
    if not username:
        return

    # Garante que os dados a serem salvos sejam uma lista
    if not isinstance(lembretes_data, list):
        print("ERRO: Tentativa de salvar lembretes com dados que não são uma lista.")
        return

    data_json_string = json.dumps(lembretes_data, ensure_ascii=False, indent=4)
    encrypted_data_string = encrypt_file_content_general(data_json_string)

    caminho_arquivo = f"dados/lembretes/lembretes_{username}.json"
    mensagem_commit = f"Atualiza lembretes do usuario {username}"
    
    try:
        salvar_dados_no_github(caminho_arquivo, encrypted_data_string, mensagem_commit)
        print(f"Lembretes de '{username}' salvos no GitHub.")
    except Exception as e:
        st.error(f"Erro ao salvar lembretes no GitHub: {e}")