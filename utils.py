# utils.py

import streamlit as st
import os
import json
import boto3
import re
from dotenv import load_dotenv
from pathlib import Path
from cryptography.fernet import Fernet
from github import Github, UnknownObjectException

# Garante que as variáveis de ambiente do .env sejam carregadas
load_dotenv()

# --- Conexão Centralizada com o Supabase ---
# Definindo supabase como None, já que não será usado para preferências.
# As linhas de conexão com Supabase foram removidas/comentadas.
supabase = None 

# --- INICIALIZAÇÃO DAS CHAVES DE CRIPTOGRAFIA FERNTE ---

# Chave para criptografia de preferências (conteúdo total do arquivo preferencias_*.json)
ENCRYPTION_KEY_PREFERENCES_STR = st.secrets.get(
    "ENCRYPTION_KEY_PREFERENCES") or os.getenv("ENCRYPTION_KEY_PREFERENCES")
fernet_preferences = None
if ENCRYPTION_KEY_PREFERENCES_STR:
    try:
        fernet_preferences = Fernet(ENCRYPTION_KEY_PREFERENCES_STR.encode())
        # print("Chave Fernet 'preferencias' carregada com sucesso.") # Debug removido
    except Exception as e:
        print(f"ERRO: Falha ao inicializar Fernet 'preferencias': {e}")
        st.error(
            "Erro de configuração de criptografia para preferências. Verifique ENCRYPTION_KEY_PREFERENCES.")
else:
    print("AVISO: Variável ENCRYPTION_KEY_PREFERENCES não encontrada.")

# Chave para criptografia de usuários (assinaturas.json, nomes de arquivo de chat)
ENCRYPTION_KEY_USERS_STR = st.secrets.get(
    "ENCRYPTION_KEY_USERS") or os.getenv("ENCRYPTION_KEY_USERS")
fernet_users = None
if ENCRYPTION_KEY_USERS_STR:
    try:
        fernet_users = Fernet(ENCRYPTION_KEY_USERS_STR.encode())
        # print("Chave Fernet 'usuarios' carregada com sucesso.") # Debug removido
    except Exception as e:
        print(f"ERRO: Falha ao inicializar Fernet 'usuarios': {e}")
        st.error(
            "Erro de configuração de criptografia para usuários. Verifique ENCRYPTION_KEY_USERS.")
else:
    print("AVISO: Variável ENCRYPTION_KEY_USERS não encontrada.")

# Chave para criptografia geral (feedback.json, memoria_jarvis.json)
ENCRYPTION_KEY_GENERAL_STR = st.secrets.get(
    "ENCRYPTION_KEY_GENERAL") or os.getenv("ENCRYPTION_KEY_GENERAL")
fernet_general = None
if ENCRYPTION_KEY_GENERAL_STR:
    try:
        fernet_general = Fernet(ENCRYPTION_KEY_GENERAL_STR.encode())
        # print("Chave Fernet 'geral' carregada com sucesso.") # Debug removido
    except Exception as e:
        print(f"ERRO: Falha ao inicializar Fernet 'geral': {e}")
        st.error(
            "Erro de configuração de criptografia geral. Verifique ENCRYPTION_KEY_GENERAL.")
else:
    print("AVISO: Variável ENCRYPTION_KEY_GENERAL não encontrada.")

# --- FUNÇÕES DE CRIPTOGRAFIA/DESCRIPTOGRAFIA ---


def encrypt_string_users(text_string):
    """Criptografa uma string usando a chave Fernet de usuários."""
    if fernet_users:
        return fernet_users.encrypt(text_string.encode()).decode()
    return text_string


def decrypt_string_users(encrypted_text_string):
    """Descriptografa uma string usando a chave Fernet de usuários."""
    if fernet_users:
        try:
            return fernet_users.decrypt(encrypted_text_string.encode()).decode()
        except Exception as e:
            print(
                f"ERRO: Falha ao descriptografar string de usuário. Retornando original. Erro: {e}")
            return encrypted_text_string
    return encrypted_text_string


def decrypt_file_content_general(encrypted_data_string):
    """
    Descriptografa uma string criptografada usando a chave Fernet geral.
    Espera uma string de texto criptografado (base64) e retorna a string decodificada.
    """
    if fernet_general:
        try:
            # 1. Converte a string de entrada para bytes, pois Fernet.decrypt espera bytes.
            encrypted_bytes_for_fernet = encrypted_data_string.encode()
            
            # 2. Tenta descriptografar. O resultado deve ser bytes se for bem-sucedido.
            decrypted_bytes = fernet_general.decrypt(encrypted_bytes_for_fernet)
            
            # --- Verificação de Tipo para Robustez ---
            if not isinstance(decrypted_bytes, bytes):
                # print(f"ERRO CRÍTICO DE DESCRIPTOGRAFIA: O resultado de Fernet.decrypt NÃO é do tipo bytes. Tipo retornado: {type(decrypted_bytes)}") # Debug removido
                return None
            # --- Fim da Verificação de Tipo ---

            # 3. Decodifica os bytes descriptografados para uma string UTF-8.
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            print(
                f"ERRO: Falha ao descriptografar conteúdo de arquivo geral. Tipo do Erro: {type(e).__name__}, Mensagem: {e}")
            return None 
    else:
        print("AVISO: Chave de criptografia 'fernet_general' não inicializada. Verifique ENCRYPTION_KEY_GENERAL.")
    return None


def encrypt_file_content_general(data_json_string):
    """Criptografa uma string JSON usando a chave Fernet geral."""
    if fernet_general:
        return fernet_general.encrypt(data_json_string.encode()).decode()
    return data_json_string

# --- FUNÇÕES AUXILIARES PARA INTERAÇÃO COM GITHUB ---


@st.cache_resource
def _get_github_repo():
    """Inicializa e retorna o objeto do repositório GitHub."""
    try:
        github_token = st.secrets["GITHUB_TOKEN"]
        repo_nome = st.secrets["GITHUB_REPO"]
        g = Github(github_token)
        repo = g.get_repo(repo_nome)
        return repo
    except Exception as e:
        st.error(f"Erro ao conectar com GitHub: {e}")
        return None


@st.cache_data(ttl=300)  # Cache para otimizar leituras repetidas
def carregar_dados_do_github(caminho_arquivo):
    """Carrega o conteúdo bruto de um arquivo do repositório do GitHub."""
    repo = _get_github_repo()
    if not repo:
        return None
    try:
        arquivo = repo.get_contents(caminho_arquivo)
        conteudo_decodificado = arquivo.decoded_content.decode("utf-8")
        return conteudo_decodificado
    except UnknownObjectException:
        return None
    except Exception as e:
        st.error(f"Erro ao carregar do GitHub ({caminho_arquivo}): {e}")
        return None


def salvar_dados_no_github(caminho_arquivo, conteudo, mensagem_commit):
    """Cria ou atualiza um arquivo no repositório do GitHub."""
    repo = _get_github_repo()
    if not repo:
        return False
    try:
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
        carregar_dados_do_github.clear()  # Limpa o cache para garantir leitura fresca
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no GitHub: {e}")
        return False


def excluir_arquivo_do_github(caminho_arquivo, mensagem_commit):
    """Exclui um arquivo do repositório do GitHub."""
    repo = _get_github_repo()
    if not repo:
        return False
    try:
        arquivo = repo.get_contents(caminho_arquivo)
        repo.delete_file(
            path=arquivo.path,
            message=mensagem_commit,
            sha=arquivo.sha
        )
        carregar_dados_do_github.clear()
        return True
    except UnknownObjectException:
        return True
    except Exception as e:
        st.error(f"Erro ao excluir do GitHub: {e}")
        return False

# --- FUNÇÕES GENÉRICAS PARA CARREGAR/SALVAR JSON CRIPTOGRAFADO ---


def _load_encrypted_json_from_github(caminho_arquivo):
    """Carrega, descriptografa e decodifica um JSON de um arquivo GitHub."""
    encrypted_file_content = carregar_dados_do_github(caminho_arquivo)
    if encrypted_file_content:
        try:
            decrypted_file_content = decrypt_file_content_general(
                encrypted_file_content)
            if decrypted_file_content is None: # Se a descriptografia falhar, retorna None
                return None
            return json.loads(decrypted_file_content)
        except json.JSONDecodeError:
            # print(f"AVISO: Conteúdo do GitHub em '{caminho_arquivo}' não é JSON válido após descriptografia.") # Debug removido
            return None
        except Exception as e:
            # print(f"ERRO: Falha ao descriptografar/decodificar JSON de '{caminho_arquivo}': {e}") # Debug removido
            return None
    return None


def _save_json_to_github(caminho_arquivo, data, mensagem_commit):
    """Codifica, criptografa e salva um JSON em um arquivo GitHub."""
    try:
        conteudo_json = json.dumps(data, ensure_ascii=False)
        conteudo_criptografado = encrypt_file_content_general(conteudo_json)
        return salvar_dados_no_github(caminho_arquivo, conteudo_criptografado, mensagem_commit)
    except Exception as e:
        print(f"ERRO: Falha ao salvar JSON em '{caminho_arquivo}': {e}")
        return False

# --- FUNÇÕES DE PREFERÊNCIAS ---

# A função normalize_preference_key está definida aqui para garantir que esteja acessível
def normalize_preference_key(key_string):
    """Normaliza uma string de chave para um formato consistente."""
    if not isinstance(key_string, str):
        return str(key_string).strip().lower()
    normalized_key = key_string.strip().lower()
    normalized_key = re.sub(r'\s+', '_', normalized_key)
    normalized_key = re.sub(r'[^a-z0-9_]', '', normalized_key)
    return normalized_key


def carregar_preferencias(username):
    """
    Carrega as preferências APENAS do GitHub.
    Descriptografa o conteúdo e normaliza as chaves.
    """
    # print(f"[DEBUG - Carregar Prefs] Carregando preferências para '{username}' APENAS do GitHub.") # Debug removido
    caminho_arquivo = f"preferencias/prefs_{username}.json"
    data_loaded_raw = _load_encrypted_json_from_github(caminho_arquivo)

    if data_loaded_raw:
        normalized_preferences = {normalize_preference_key(
            k): v for k, v in data_loaded_raw.items()}
        # print(f"[DEBUG - Carregar Prefs] Preferências NORMALIZADAS do GitHub: {normalized_preferences}") # Debug removido
        return normalized_preferences
    # print(f"[DEBUG - Carregar Prefs] Nenhuma preferência encontrada no GitHub para '{username}'. Retornando dicionário vazio.") # Debug removido
    return {}


def salvar_preferencias(data, username):
    """
    Salva as preferências APENAS no GitHub.
    Normaliza as chaves das preferências.
    """
    data_to_save_normalized_keys = {
        normalize_preference_key(k): v for k, v in data.items()}
    
    # print(f"[DEBUG - Salvar Prefs] Dados normalizados a serem salvos no GitHub para '{username}': {data_to_save_normalized_keys}") # Debug removido

    caminho_arquivo = f"preferencias/prefs_{username}.json"
    mensagem_commit = f"Atualiza preferencias do usuario {username}"
    
    # Salva apenas no GitHub
    if _save_json_to_github(caminho_arquivo, data_to_save_normalized_keys, mensagem_commit):
        # print(f"Preferências de '{username}' salvas no GitHub.") # Debug removido
        return True
    else:
        print(f"ERRO: Falha ao salvar preferências no GitHub para '{username}'.")
        return False


# --- FUNÇÕES DE EMOÇÕES ---
def carregar_emocoes(username):
    """
    Carrega emoções do usuário do GitHub (criptografadas).
    Retorna um dicionário ou lista de emoções.
    """
    caminho = f"emocoes/emocoes_{username}.json"
    emocoes_carregadas = _load_encrypted_json_from_github(caminho)
    return emocoes_carregadas if emocoes_carregadas is not None else []


def salvar_emocoes(emocoes, username):
    """
    Salva emoções no GitHub (criptografado), uma lista ou dicionário.
    """
    caminho = f"emocoes/emocoes_{username}.json"
    mensagem_commit = f"Atualiza emoções do usuário {username}"
    return _save_json_to_github(caminho, emocoes, mensagem_commit)


def excluir_emocoes(username):
    """
    Exclui o arquivo de emoções de um usuário do GitHub.
    """
    caminho = f"emocoes/emocoes_{username}.json"
    mensagem_commit = f"Exclui todas as emoções do usuário {username}"
    return excluir_arquivo_do_github(caminho, mensagem_commit)

# --- FUNÇÕES DE REFLEXÕES ---


def salvar_reflexoes(reflexoes_dict, username):
    caminho = f"reflexoes/reflexoes_{username}.json"
    mensagem_commit = f"Salva reflexões do usuário {username}"
    return _save_json_to_github(caminho, reflexoes_dict, mensagem_commit)


def carregar_reflexoes(username):
    caminho = f"reflexoes/reflexoes_{username}.json"
    reflexoes_carregadas = _load_encrypted_json_from_github(caminho)
    return reflexoes_carregadas if reflexoes_carregadas is not None else []

# --- FUNÇÕES DE CHATS ---


def carregar_chats(username):
    """
    Carrega o histórico de chats do usuário do GitHub (criptografado).
    Retorna um dicionário de chats para o usuário ou um dicionário vazio se não houver.
    """
    caminho = f"chats/{username}_chats.json"
    chats_carregados = _load_encrypted_json_from_github(caminho)
    return chats_carregados if chats_carregados is not None else {}


def salvar_chats(username):
    """
    Salva o histórico de chats do usuário no GitHub (criptografado)
    diretamente de st.session_state.chats[username].
    """
    if "chats" not in st.session_state or username not in st.session_state.chats:
        print(f"[AVISO] Tentativa de salvar chats para {username}, mas não há dados em st.session_state.chats.")
        return False

    chats_do_usuario = st.session_state.chats[username]
    caminho = f"chats/{username}_chats.json"
    mensagem_commit = f"Atualiza histórico de chats do usuário {username}"
    if _save_json_to_github(caminho, chats_do_usuario, mensagem_commit):
        # print(f"Chats de '{username}' salvos no GitHub.") # Debug removido
        return True
    else:
        print(f"ERRO: Falha ao salvar chats de {username}.")
        return False
    
    # --- FUNÇÕES DE ANOTAÇÕES ---

def salvar_anotacoes(anotacoes_dict, username):
    """
    Salva o dicionário de anotações do usuário no GitHub (criptografado).
    """
    caminho = f"anotacoes/anotacoes_{username}.json"
    mensagem_commit = f"Atualiza anotações do usuario {username}"
    # Garante que o diretório exista no repositório (o GitHub cria se não existir)
    # A função _save_json_to_github já lida com a criação do arquivo.
    return _save_json_to_github(caminho, anotacoes_dict, mensagem_commit)


def carregar_anotacoes(username):
    """
    Carrega as anotações do usuário a partir de um arquivo JSON no GitHub.
    Retorna um dicionário vazio se o arquivo não existir.
    """
    caminho = f"anotacoes/anotacoes_{username}.json"
    anotacoes_carregadas = _load_encrypted_json_from_github(caminho)
    return anotacoes_carregadas if anotacoes_carregadas is not None else {}

def analisar_imagem_com_rekognition(image_bytes, tipo_analise="labels"):
    """
    Analisa uma imagem usando o Amazon Rekognition de forma segura.
    Esta função agora vive em utils.py para melhor organização.
    Retorna um dicionário com a resposta ou None em caso de erro.
    """
    try:
        # Carrega as credenciais de forma segura, como você já faz
        aws_access_key = st.secrets.get("AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = st.secrets.get("AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
        
        if not aws_access_key or not aws_secret_key:
            st.error("As credenciais da AWS (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) não estão configuradas nos Secrets.")
            return None

        # Conecta-se ao serviço Rekognition
        rekognition_client = boto3.client(
            'rekognition',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name='us-east-1'  # Mude se necessário
        )

        st.info(f"🔎 Analisando imagem com Amazon Rekognition (modo: {tipo_analise})...")

        # Chama a API correta baseada no tipo de análise solicitado
        if tipo_analise == "labels":
            response = rekognition_client.detect_labels(Image={'Bytes': image_bytes}, MaxLabels=15, MinConfidence=80)
        elif tipo_analise == "faces":
            response = rekognition_client.detect_faces(Image={'Bytes': image_bytes}, Attributes=['ALL'])
        elif tipo_analise == "text":
            response = rekognition_client.detect_text(Image={'Bytes': image_bytes})
        else:
            return {"error": "Tipo de análise não suportado."}
        
        return response

    except Exception as e:
        st.error(f"Ocorreu um erro ao conectar com o Amazon Rekognition: {e}")
        return None