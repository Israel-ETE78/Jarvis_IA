# migrar_memoria_jarvis.py

import json
import os
from pathlib import Path
from memoria_jarvis_manager import MEMORIA_JARVIS_FILE_PATH # Importa o caminho do arquivo
from utils import encrypt_file_content_general, decrypt_file_content_general, fernet_general

def migrate_memoria_jarvis():
    print(f"Iniciando migração para '{MEMORIA_JARVIS_FILE_PATH}'...")
    if not os.path.exists(MEMORIA_JARVIS_FILE_PATH):
        print("Arquivo de memória não encontrado. Nenhuma migração necessária.")
        return

    try:
        with open(MEMORIA_JARVIS_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        try: # Tenta descriptografar primeiro para verificar se já está criptografado
            decrypted_content = decrypt_file_content_general(content)
            current_memoria = json.loads(decrypted_content)
            print("Conteúdo existente parece criptografado e foi carregado.")
            print("Conteúdo já criptografado. Nenhuma ação necessária.")
            return
        except (json.JSONDecodeError, Exception) as e:
            print(f"Conteúdo existente não parece criptografado ou é JSON inválido: {e}. Tentando carregar como texto claro.")
            current_memoria = json.loads(content) # Carrega como JSON em texto claro
            
        print("Criptografando o conteúdo do arquivo de memória...")
        json_string = json.dumps(current_memoria, indent=4, ensure_ascii=False)
        encrypted_string = encrypt_file_content_general(json_string)

        with open(MEMORIA_JARVIS_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(encrypted_string)
        print("Migração concluída: memoria_jarvis.json agora está criptografado.")

    except json.JSONDecodeError as e:
        print(f"ERRO FATAL: Conteúdo do arquivo '{MEMORIA_JARVIS_FILE_PATH}' não é um JSON válido. Não é possível migrar. Erro: {e}")
    except Exception as e:
        print(f"ERRO inesperado durante a migração de '{MEMORIA_JARVIS_FILE_PATH}': {e}")

if __name__ == "__main__":
    if fernet_general is None:
        print("ERRO: Objeto Fernet para criptografia geral não inicializado. Verifique ENCRYPTION_KEY_GENERAL no seu .env e utils.py.")
    else:
        migrate_memoria_jarvis()