import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
from cryptography.fernet import Fernet
from github import Github, UnknownObjectException

# --- CARREGAMENTO DE CONFIGURAÇÕES E VARIÁVEIS DE AMBIENTE ---
# Essencial para rodar fora do Streamlit
print("Iniciando o script verificador de lembretes...")
load_dotenv()

# Carrega as configurações do ambiente (local ou nuvem)
def get_secret(secret_name):
    # Primeiro tenta pelo Streamlit secrets (se o script rodar nesse contexto)
    try:
        import streamlit as st
        return st.secrets.get(secret_name)
    except (ImportError, Exception):
        # Fallback para variáveis de ambiente
        return os.getenv(secret_name)

# Configs de E-mail
EMAIL_REMETENTE = get_secret("GMAIL_USER")
SENHA_APP = get_secret("GMAIL_APP_PASSWORD")

# Configs do GitHub
GITHUB_TOKEN = get_secret("GITHUB_TOKEN")
REPO_NOME = get_secret("GITHUB_REPO")

# Configs de Criptografia
ENCRYPTION_KEY_GENERAL_STR = get_secret("ENCRYPTION_KEY_GENERAL")
fernet_general = Fernet(ENCRYPTION_KEY_GENERAL_STR.encode()) if ENCRYPTION_KEY_GENERAL_STR else None

# --- FUNÇÕES AUXILIARES ADAPTADAS PARA O SCRIPT ---

def carregar_dados_remotos(caminho_arquivo, g_repo):
    """Carrega conteúdo de um arquivo do GitHub."""
    try:
        arquivo = g_repo.get_contents(caminho_arquivo)
        return arquivo.decoded_content.decode("utf-8")
    except UnknownObjectException:
        print(f"Arquivo não encontrado em '{caminho_arquivo}'.")
        return None
    except Exception as e:
        print(f"Erro ao carregar do GitHub ({caminho_arquivo}): {e}")
        return None

def salvar_dados_remotos(caminho_arquivo, conteudo, mensagem_commit, g_repo):
    """Cria ou atualiza um arquivo no GitHub."""
    try:
        try:
            arquivo_existente = g_repo.get_contents(caminho_arquivo)
            g_repo.update_file(
                path=caminho_arquivo,
                message=mensagem_commit,
                content=conteudo,
                sha=arquivo_existente.sha
            )
        except UnknownObjectException:
            g_repo.create_file(
                path=caminho_arquivo,
                message=mensagem_commit,
                content=conteudo
            )
        return True
    except Exception as e:
        print(f"Erro ao salvar no GitHub ({caminho_arquivo}): {e}")
        return False

def decrypt_content(encrypted_data):
    """Descriptografa conteúdo usando a chave geral."""
    if fernet_general:
        try:
            return fernet_general.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return encrypted_data # Retorna original se falhar
    return encrypted_data

def encrypt_content(data_json_string):
    """Criptografa conteúdo usando a chave geral."""
    if fernet_general:
        return fernet_general.encrypt(data_json_string.encode()).decode()
    return data_json_string

def enviar_email_notificacao(destinatario, assunto, mensagem):
    if not EMAIL_REMETENTE or not SENHA_APP:
        print(f"ERRO: Credenciais de e-mail não configuradas. Não é possível notificar {destinatario}.")
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = destinatario
        msg.set_content(mensagem)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_REMETENTE, SENHA_APP)
            smtp.send_message(msg)
        print(f"E-mail de lembrete enviado com sucesso para {destinatario}.")
        return True
    except Exception as e:
        print(f"ERRO ao enviar e-mail para {destinatario}: {e}")
        return False

# --- LÓGICA PRINCIPAL DO VERIFICADOR ---
def verificar_lembretes_e_notificar():
    if not all([GITHUB_TOKEN, REPO_NOME, fernet_general]):
        print("ERRO FATAL: Configurações de GitHub ou Criptografia ausentes.")
        return

    print("Conectando ao GitHub...")
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NOME)
    
    agora = datetime.now()
    print(f"Verificação iniciada em: {agora.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Carregar o arquivo de assinaturas principal (NÃO criptografado)
    print("Carregando assinaturas...")
    conteudo_assinaturas = carregar_dados_remotos("dados/assinaturas.json", repo)
    if not conteudo_assinaturas:
        print("Arquivo de assinaturas não encontrado ou vazio. Finalizando.")
        return
    
    assinaturas = json.loads(conteudo_assinaturas)

    # 2. Iterar sobre cada usuário
    for username, user_data in assinaturas.items():
        print(f"\nVerificando lembretes para o usuário: '{username}'")
        
        # 3. Carregar e descriptografar os lembretes do usuário
        caminho_lembretes = f"dados/lembretes/lembretes_{username}.json"
        conteudo_lembretes_enc = carregar_dados_remotos(caminho_lembretes, repo)
        
        if not conteudo_lembretes_enc:
            print(f"Nenhum arquivo de lembretes encontrado para '{username}'.")
            continue

        lembretes = json.loads(decrypt_content(conteudo_lembretes_enc))
        
        lembretes_modificados = False
        
        # 4. Verificar cada lembrete
        for lembrete in lembretes:
            data_lembrete = datetime.strptime(lembrete['data_lembrete'], "%Y-%m-%d %H:%M:%S")
            
            # Condição: a data passou, o status é pendente e a notificação não foi enviada
            if agora >= data_lembrete and lembrete.get('status', 'pendente') == 'pendente' and not lembrete.get('notificacao_enviada', False):
                print(f"-> Lembrete '{lembrete['titulo']}' de '{username}' está vencido. Enviando notificação...")
                
                # Montar e enviar e-mail
                email_usuario = user_data.get("email")
                if not email_usuario:
                    print(f"ERRO: Usuário '{username}' não possui e-mail cadastrado.")
                    continue

                assunto = f"🔔 Lembrete Jarvis IA: {lembrete['titulo']}"
                mensagem = (
                    f"Olá, {username}!\n\n"
                    f"Este é um lembrete para:\n\n"
                    f"Título: {lembrete['titulo']}\n"
                    f"Data/Hora: {data_lembrete.strftime('%d/%m/%Y às %H:%M')}\n\n"
                )
                if lembrete['descricao']:
                    mensagem += f"Descrição:\n{lembrete['descricao']}\n\n"
                
                mensagem += "Atenciosamente,\nEquipe Jarvis IA"
                
                if enviar_email_notificacao(email_usuario, assunto, mensagem):
                    lembrete['notificacao_enviada'] = True
                    lembretes_modificados = True
        
        # 5. Se algum lembrete foi modificado, salvar o arquivo de volta no GitHub
        if lembretes_modificados:
            print(f"Salvando lembretes atualizados para '{username}'...")
            conteudo_para_salvar = json.dumps(lembretes, indent=4, ensure_ascii=False)
            conteudo_enc_para_salvar = encrypt_content(conteudo_para_salvar)
            salvar_dados_remotos(caminho_lembretes, conteudo_enc_para_salvar, f"Atualiza status de notificação de lembretes para {username}", repo)

    print("\nVerificação de lembretes concluída.")

# --- PONTO DE ENTRADA DO SCRIPT ---
if __name__ == "__main__":
    verificar_lembretes_e_notificar()