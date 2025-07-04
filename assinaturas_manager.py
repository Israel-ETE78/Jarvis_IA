# assinaturas_manager.py

import os
import json
from pathlib import Path
from utils import encrypt_string_users, decrypt_string_users, fernet_users # Importa as funções Fernet de usuários

ASSINATURAS_FILE_PATH = "dados/assinaturas.json"

# --- Funções Auxiliares para Criptografar/Descriptografar Valores Internos ---
# (Usam encrypt_string_users/decrypt_string_users)
def _encrypt_signature_value(value):
    """Criptografa um valor individual de assinatura (exceto senhas)."""
    if isinstance(value, str):
        return encrypt_string_users(value)
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return encrypt_string_users(str(value))
    return value # Retorna o valor original se não for string, bool, int, float

def _decrypt_signature_value(encrypted_value):
    """Descriptografa um valor individual de assinatura (exceto senhas)."""
    if isinstance(encrypted_value, str):
        decrypted_str = decrypt_string_users(encrypted_value)
        if decrypted_str.lower() == 'true': return True
        if decrypted_str.lower() == 'false': return False
        try: return int(decrypted_str)
        except ValueError: pass
        try: return float(decrypted_str)
        except ValueError: pass
        return decrypted_str
    return encrypted_value

def _load_raw_signatures_data():
    """Carrega o conteúdo bruto do arquivo de assinaturas (com chaves/valores criptografados)."""
    if not os.path.exists(ASSINATURAS_FILE_PATH):
        return {}
    try:
        with open(ASSINATURAS_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERRO: Conteúdo de '{ASSINATURAS_FILE_PATH}' não é um JSON válido. Erro: {e}")
        return {}
    except Exception as e:
        print(f"ERRO ao ler '{ASSINATURAS_FILE_PATH}': {e}")
        return {}

def _save_raw_signatures_data(data):
    """Salva o conteúdo bruto no arquivo de assinaturas (com chaves/valores criptografados)."""
    Path(ASSINATURAS_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(ASSINATURAS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Dados de assinaturas salvos em '{ASSINATURAS_FILE_PATH}'.")
    except Exception as e:
        print(f"ERRO ao salvar em '{ASSINATURAS_FILE_PATH}': {e}")

def carregar_assinaturas():
    """
    Carrega todas as assinaturas, descriptografando nomes de usuário (chaves)
    e os valores de seus atributos (exceto a senha).
    """
    raw_data = _load_raw_signatures_data()
    decrypted_signatures = {}
    for encrypted_username_key, user_info_encrypted in raw_data.items():
        decrypted_username_plain = decrypt_string_users(encrypted_username_key)
        
        decrypted_user_info = {}
        for key, value in user_info_encrypted.items():
            if key == "senha":
                decrypted_user_info[key] = value # Mantém o hash da senha
            else:
                decrypted_user_info[key] = _decrypt_signature_value(value) # Descriptografa outros valores
        
        decrypted_signatures[decrypted_username_plain] = decrypted_user_info
    print(f"Assinaturas carregadas e descriptografadas de '{ASSINATURAS_FILE_PATH}'.")
    return decrypted_signatures

def salvar_assinaturas(signatures_data):
    """
    Salva todas as assinaturas, criptografando nomes de usuário (chaves)
    e os valores de seus atributos (exceto a senha).
    """
    encrypted_signatures = {}
    for username_plain, user_info_plain in signatures_data.items():
        encrypted_username_key = encrypt_string_users(username_plain)
        
        encrypted_user_info = {}
        for key, value in user_info_plain.items():
            if key == "senha":
                encrypted_user_info[key] = value # Mantém o hash da senha
            else:
                encrypted_user_info[key] = _encrypt_signature_value(value) # Criptografa outros valores
        
        encrypted_signatures[encrypted_username_key] = encrypted_user_info
    _save_raw_signatures_data(encrypted_signatures)
    print(f"Assinaturas salvas em '{ASSINATURAS_FILE_PATH}' (criptografadas).")

def adicionar_assinatura(username_plain, user_info):
    """Adiciona ou atualiza uma assinatura. Salva o arquivo."""
    all_signatures = carregar_assinaturas() # Carrega todos (descriptografados)
    all_signatures[username_plain] = user_info
    salvar_assinaturas(all_signatures) # Salva tudo (criptografado)
    print(f"Assinatura para '{username_plain}' adicionada/atualizada.")

def remover_assinatura(username_plain):
    """Remove uma assinatura. Salva o arquivo."""
    all_signatures = carregar_assinaturas() # Carrega todos (descriptografados)
    if username_plain in all_signatures:
        del all_signatures[username_plain]
        salvar_assinaturas(all_signatures) # Salva tudo (criptografado)
        print(f"Assinatura para '{username_plain}' removida.")
        return True
    print(f"AVISO: Assinatura para '{username_plain}' não encontrada para remoção.")
    return False