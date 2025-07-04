# chat_history_manager.py

import os
import json
from pathlib import Path
from utils import encrypt_string_users, decrypt_string_users # Importa as funções Fernet de usuários

CHATS_HISTORY_FOLDER = "dados/chats_historico"

def get_user_history_file_path(username_plain):
    """
    Retorna o caminho completo para o arquivo de histórico de chat de um usuário.
    O nome do arquivo é o nome de usuário criptografado.
    """
    if not isinstance(username_plain, str) or not username_plain:
        raise ValueError("Nome de usuário inválido para gerar caminho do histórico.")
        
    encrypted_username_filename = encrypt_string_users(username_plain)
    # Garante que o nome do arquivo criptografado seja seguro para o sistema de arquivos
    safe_filename = encrypted_username_filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_')
    return Path(CHATS_HISTORY_FOLDER) / f"{safe_filename}.json"

def carregar_historico_chat(username_plain):
    """
    Carrega o histórico de chat de um usuário específico.
    Abre o arquivo correspondente ao nome de usuário criptografado.
    """
    file_path = get_user_history_file_path(username_plain)

    if not file_path.exists():
        print(f"Arquivo de histórico de chat para '{username_plain}' não encontrado em '{file_path}'. Retornando vazio.")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            chat_history = json.load(f)
        print(f"Histórico de chat para '{username_plain}' carregado de '{file_path}'.")
        return chat_history
    except json.JSONDecodeError as e:
        print(f"ERRO: Conteúdo do arquivo de histórico de chat para '{username_plain}' não é um JSON válido. Erro: {e}")
        return []
    except Exception as e:
        print(f"ERRO ao carregar histórico de chat para '{username_plain}' de '{file_path}': {e}")
        return []

def salvar_historico_chat(username_plain, chat_history):
    """
    Salva o histórico de chat de um usuário específico.
    Cria a pasta se não existir e salva no arquivo correspondente ao nome de usuário criptografado.
    """
    Path(CHATS_HISTORY_FOLDER).mkdir(parents=True, exist_ok=True)
    
    file_path = get_user_history_file_path(username_plain)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, indent=4, ensure_ascii=False)
        print(f"Histórico de chat para '{username_plain}' salvo em '{file_path}'.")
    except Exception as e:
        print(f"ERRO ao salvar histórico de chat para '{username_plain}' em '{file_path}': {e}")

def remover_historico_chat(username_plain):
    """
    Remove o arquivo de histórico de chat de um usuário específico.
    """
    file_path = get_user_history_file_path(username_plain)
    if file_path.exists():
        try:
            os.remove(file_path)
            print(f"Histórico de chat para '{username_plain}' removido: '{file_path}'.")
            return True
        except Exception as e:
            print(f"ERRO ao remover histórico de chat para '{username_plain}' em '{file_path}': {e}")
            return False
    print(f"AVISO: Histórico de chat para '{username_plain}' não encontrado para remoção em '{file_path}'.")
    return False