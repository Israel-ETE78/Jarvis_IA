# chat_history_manager.py

import json
import os
from pathlib import Path
from utils import encrypt_string_users, decrypt_string_users, fernet_users

# Define a pasta raiz onde os dados são armazenados
DATA_FOLDER = "dados"
# Define a nova subpasta para os históricos de chat
CHAT_HISTORY_SUBFOLDER = "chats_historico"
# Constrói o caminho completo para a pasta de históricos de chat
CHAT_HISTORY_FOLDER_PATH = Path(DATA_FOLDER) / CHAT_HISTORY_SUBFOLDER

def _get_chat_file_path(username_plain):
    """
    Retorna o caminho completo do arquivo de histórico de chat para um usuário.
    O nome do arquivo é o nome de usuário criptografado.
    """
    if fernet_users is None:
        raise ValueError("A chave Fernet para usuários não está inicializada. Verifique ENCRYPTION_KEY_USERS no seu .env e utils.py.")
    
    encrypted_username = encrypt_string_users(username_plain)
    return CHAT_HISTORY_FOLDER_PATH / f"{encrypted_username}.json"

def carregar_historico_chat(username_plain):
    """
    Carrega o histórico de chat de um usuário específico.
    Retorna uma lista de mensagens.
    """
    file_path = _get_chat_file_path(username_plain)
    
    if not file_path.exists():
        return [] # Retorna uma lista vazia se o arquivo não existir

    if fernet_users is None:
        raise ValueError("A chave Fernet para usuários não está inicializada. Não é possível descriptografar o histórico de chat.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            encrypted_content = f.read()
            if not encrypted_content: # Arquivo vazio
                return []
            
            # O conteúdo do arquivo é uma única string JSON criptografada
            decrypted_json_str = decrypt_string_users(encrypted_content)
            return json.loads(decrypted_json_str)
    except Exception as e:
        print(f"ERRO ao carregar histórico de chat para {username_plain} de {file_path}: {e}")
        # Em caso de erro (ex: arquivo corrompido ou não criptografado corretamente), retorna vazio
        return []

def salvar_historico_chat(username_plain, chat_history):
    """
    Salva o histórico de chat de um usuário específico.
    Espera uma lista de mensagens.
    """
    # Garante que a pasta existe antes de salvar
    CHAT_HISTORY_FOLDER_PATH.mkdir(parents=True, exist_ok=True)
    
    file_path = _get_chat_file_path(username_plain)

    if fernet_users is None:
        raise ValueError("A chave Fernet para usuários não está inicializada. Não é possível criptografar o histórico de chat.")

    try:
        # Converte a lista de mensagens para uma string JSON
        json_str = json.dumps(chat_history, ensure_ascii=False, indent=4)
        # Criptografa a string JSON completa
        encrypted_content = encrypt_string_users(json_str)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(encrypted_content)
        # print(f"Histórico de chat para {username_plain} salvo em {file_path}")
    except Exception as e:
        print(f"ERRO ao salvar histórico de chat para {username_plain} em {file_path}: {e}")

def get_all_chat_history_files():
    """
    Retorna uma lista de todos os caminhos de arquivo de histórico de chat criptografados.
    """
    if not CHAT_HISTORY_FOLDER_PATH.exists():
        return []
    return list(CHAT_HISTORY_FOLDER_PATH.glob("*.json"))

def delete_chat_history(username_plain):
    """
    Deleta o arquivo de histórico de chat de um usuário específico.
    """
    file_path = _get_chat_file_path(username_plain)
    if file_path.exists():
        try:
            os.remove(file_path)
            print(f"Histórico de chat para {username_plain} deletado.")
            return True
        except Exception as e:
            print(f"ERRO ao deletar histórico de chat para {username_plain}: {e}")
            return False
    return False