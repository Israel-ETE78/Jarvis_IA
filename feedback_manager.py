# feedback_manager.py

import os
import json
from pathlib import Path
from utils import encrypt_file_content_general, decrypt_file_content_general # Funções de criptografia geral

FEEDBACK_FILE_PATH = "dados/feedback.json"

def carregar_feedback():
    """
    Carrega os dados de feedback do arquivo, descriptografando o conteúdo inteiro.
    """
    if not os.path.exists(FEEDBACK_FILE_PATH):
        print(f"Arquivo de feedback '{FEEDBACK_FILE_PATH}' não encontrado. Retornando vazio.")
        return [] # Assumindo que feedback é uma lista de itens

    try:
        with open(FEEDBACK_FILE_PATH, 'r', encoding='utf-8') as f:
            encrypted_content = f.read()
        
        decrypted_content = decrypt_file_content_general(encrypted_content)
        
        feedback_data = json.loads(decrypted_content)
        print(f"Feedback carregado e descriptografado de '{FEEDBACK_FILE_PATH}'.")
        return feedback_data

    except json.JSONDecodeError as e:
        print(f"ERRO: Conteúdo do arquivo de feedback não é JSON válido após descriptografia. Erro: {e}")
        try: # Tenta carregar como JSON bruto se a descriptografia falhou ou não era necessária
            return json.loads(encrypted_content)
        except json.JSONDecodeError:
            print("ERRO: Conteúdo bruto do arquivo de feedback também não é JSON válido. Retornando vazio.")
            return []
    except Exception as e:
        print(f"ERRO ao carregar feedback de '{FEEDBACK_FILE_PATH}': {e}")
        return []

def salvar_feedback(feedback_data):
    """
    Salva os dados de feedback no arquivo, criptografando o conteúdo inteiro.
    """
    Path(FEEDBACK_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

    try:
        json_string = json.dumps(feedback_data, indent=4, ensure_ascii=False)
        encrypted_string = encrypt_file_content_general(json_string) # Criptografa a string JSON inteira
        
        with open(FEEDBACK_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(encrypted_string)
        print(f"Feedback salvo e criptografado em '{FEEDBACK_FILE_PATH}'.")
    except Exception as e:
        print(f"ERRO ao salvar feedback em '{FEEDBACK_FILE_PATH}': {e}")