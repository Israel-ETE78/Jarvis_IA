# mover_historicos_chat.py - CORRIGIDO PARA O CAMINHO DE ORIGEM

import os
from pathlib import Path

# Definições de caminho
# AGORA APONTA PARA A RAIZ DO SEU PROJETO JARVIS_IA, ONDE O ARQUIVO chat_historico_leidy.json ESTÁ
OLD_CHAT_HISTORY_FOLDER = Path(".") # O "." significa o diretório atual (JARVIS_IA/)

# Onde os arquivos devem ir
NEW_CHAT_HISTORY_FOLDER = Path("dados") / "chats_historico" 

def mover_arquivos_historico():
    print(f"Verificando arquivos de histórico de chat na pasta '{OLD_CHAT_HISTORY_FOLDER}' para mover para '{NEW_CHAT_HISTORY_FOLDER}'...")
    
    # Garante que a nova pasta de destino exista
    NEW_CHAT_HISTORY_FOLDER.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    
    # Procura por arquivos que começam com 'chats_historico_' e terminam com '.json'
    # Esta linha agora varre a pasta raiz do seu projeto
    for old_file_path in OLD_CHAT_HISTORY_FOLDER.glob("chats_historico_*.json"):
        if old_file_path.is_file():
            filename_without_ext = old_file_path.stem # Ex: "chats_historico_bia"
            
            # Extrai o nome de usuário (ex: "bia" de "chats_historico_bia")
            username_plain = filename_without_ext.replace("chats_historico_", "")
            
            if not username_plain:
                print(f"AVISO: Não foi possível extrair nome de usuário de '{old_file_path.name}'. Pulando.")
                continue

            print(f"Processando arquivo: {old_file_path.name} para usuário '{username_plain}'...")

            try:
                # O nome do arquivo NÃO É criptografado AINDA neste ponto,
                # apenas está sendo movido para a pasta correta.
                # A criptografia do NOME do arquivo acontecerá quando o chat_history_manager for usado para SALVAR.
                
                # Gerar o NOVO caminho completo do arquivo na subpasta de destino
                new_file_path = NEW_CHAT_HISTORY_FOLDER / old_file_path.name # Mantém o nome atual (ainda não criptografado)

                # Move o arquivo para a nova pasta
                os.rename(old_file_path, new_file_path)
                print(f"  Movido: '{old_file_path.name}' -> '{new_file_path}'")
                moved_count += 1
            except Exception as e:
                print(f"  ERRO ao mover '{old_file_path.name}': {e}")

    if moved_count > 0:
        print(f"Concluído! {moved_count} arquivo(s) de histórico de chat movido(s) para '{NEW_CHAT_HISTORY_FOLDER}'.")
        print("Lembre-se que os nomes dos arquivos ainda não estão criptografados.")
        print("Eles serão criptografados quando o chat_history_manager.py salvar os dados pela primeira vez.")
    else:
        print("Nenhum arquivo de histórico de chat encontrado para mover na pasta antiga.")

if __name__ == "__main__":
    mover_arquivos_historico()