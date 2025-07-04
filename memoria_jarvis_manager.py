# memoria_jarvis_manager.py

import os
import json
from pathlib import Path
from utils import encrypt_file_content_general, decrypt_file_content_general # Funções de criptografia geral

MEMORIA_JARVIS_FILE_PATH = "memoria_jarvis.json" # Este arquivo está na raiz do projeto

def carregar_memoria_jarvis():
    """
    Carrega o conteúdo da memória do Jarvis do arquivo, descriptografando-o.
    """
    if not os.path.exists(MEMORIA_JARVIS_FILE_PATH):
        print(f"Arquivo de memória '{MEMORIA_JARVIS_FILE_PATH}' não encontrado. Retornando memória vazia.")
        return [] # Ou {} dependendo da estrutura da sua memória

    try:
        with open(MEMORIA_JARVIS_FILE_PATH, 'r', encoding='utf-8') as f:
            encrypted_content = f.read()
        
        decrypted_content = decrypt_file_content_general(encrypted_content)
        
        memoria = json.loads(decrypted_content)
        print(f"Memória do Jarvis carregada e descriptografada de '{MEMORIA_JARVIS_FILE_PATH}'.")
        return memoria

    except json.JSONDecodeError as e:
        print(f"ERRO: Conteúdo do arquivo de memória não é JSON válido após descriptografia. Erro: {e}")
        try:
            return json.loads(encrypted_content) # Tenta carregar como JSON bruto
        except json.JSONDecodeError:
            print("ERRO: Conteúdo bruto do arquivo de memória também não é JSON válido. Retornando vazio.")
            return []
    except Exception as e:
        print(f"ERRO ao carregar memória do Jarvis de '{MEMORIA_JARVIS_FILE_PATH}': {e}")
        return []


def salvar_memoria_jarvis(memoria_data):
    """
    Salva o conteúdo da memória do Jarvis no arquivo, criptografando-o.
    """
    if not memoria_data and os.path.exists(MEMORIA_JARVIS_FILE_PATH):
        try:
            os.remove(MEMORIA_JARVIS_FILE_PATH)
            print(f"Arquivo de memória '{MEMORIA_JARVIS_FILE_PATH}' removido (memória vazia).")
            return
        except Exception as e:
            print(f"AVISO: Não foi possível remover arquivo de memória vazio: {e}")

    try:
        json_string = json.dumps(memoria_data, indent=4, ensure_ascii=False)
        encrypted_string = encrypt_file_content_general(json_string) 
        
        with open(MEMORIA_JARVIS_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(encrypted_string)
        print(f"Memória do Jarvis salva e criptografada em '{MEMORIA_JARVIS_FILE_PATH}'.")
    except Exception as e:
        print(f"ERRO ao salvar memória do Jarvis em '{MEMORIA_JARVIS_FILE_PATH}': {e}")