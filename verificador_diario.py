import json
import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações e Funções Auxiliares ---

CAMINHO_ARQUIVO = Path("dados/assinaturas.json")
EMAIL_REMETENTE = os.getenv("GMAIL_USER")
SENHA_APP = os.getenv("GMAIL_APP_PASSWORD")
EMAIL_ADMIN = os.getenv("EMAIL_ADMIN")  # Seu e-mail para receber o resumo

def carregar_assinaturas():
    if CAMINHO_ARQUIVO.exists():
        with open(CAMINHO_ARQUIVO, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_assinaturas(data):
    CAMINHO_ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_ARQUIVO, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def enviar_email(destinatario, assunto, mensagem):
    if not EMAIL_REMETENTE or not SENHA_APP:
        print("ERRO: Credenciais de e-mail não configuradas.")
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
        print(f"E-mail enviado com sucesso para {destinatario}.")
        return True
    except Exception as e:
        print(f"ERRO ao enviar e-mail para {destinatario}: {e}")
        return False

# --- Lógica Principal do Script ---
def verificar_expiracoes():
    print(f"Iniciando verificação de assinaturas em {datetime.now()}...")
    assinaturas = carregar_assinaturas()
    agora = datetime.now()
    usuarios_notificados_cliente = []
    usuarios_notificados_admin = []
    
    # É importante iterar sobre uma cópia para poder modificar o dicionário original
    for user, dados in list(assinaturas.items()):
        expiracao = datetime.strptime(dados['expiracao'], "%Y-%m-%d %H:%M:%S")
        
        # A condição agora verifica se a assinatura expirou E se um e-mail ainda não foi enviado
        if agora >= expiracao and not dados.get("email_enviado", False):
            print(f"Assinatura de '{user}' expirou.")
            
            # 1. (LÓGICA ATUALIZADA) Verifica se deve notificar o cliente
            if dados.get("notificar_cliente", True):
                print(f"Opção de notificar cliente está ativa para '{user}'. Enviando e-mail...")
                assunto_cliente = "🔔 Sua assinatura da Jarvis IA expirou"
                mensagem_cliente = f"Olá {user},\n\nSua assinatura da Jarvis IA expirou em {expiracao.strftime('%d/%m/%Y')}. Renove para continuar usando."
                enviar_email(dados["email"], assunto_cliente, mensagem_cliente)
                usuarios_notificados_cliente.append(user)
            else:
                print(f"Opção de notificar cliente está DESATIVADA para '{user}'.")

            # 2. Adiciona o usuário à lista de resumo para o admin, independentemente da notificação do cliente
            usuarios_notificados_admin.append(f"- {user} (Email: {dados['email']})")

            # 3. Atualiza o status do usuário para não notificar novamente
            assinaturas[user]["email_enviado"] = True

    # 4. Envia o e-mail de resumo para você, o admin
    if usuarios_notificados_admin and EMAIL_ADMIN:
        corpo_resumo = f"As seguintes assinaturas expiraram hoje:\n\n" + "\n".join(usuarios_notificados_admin)
        if usuarios_notificados_cliente:
            corpo_resumo += f"\n\nOs seguintes clientes foram notificados por e-mail: {', '.join(usuarios_notificados_cliente)}."
        else:
            corpo_resumo += "\n\nNenhum cliente foi notificado por e-mail (opção desativada)."
            
        enviar_email(EMAIL_ADMIN, "Resumo Diário de Assinaturas Expiradas - Jarvis IA", corpo_resumo)
    else:
        print("Nenhuma nova assinatura expirada para notificar.")

    # 5. Salva as alterações no arquivo JSON
    salvar_assinaturas(assinaturas)
    print("Verificação concluída.")

# Ponto de entrada para executar o script
if __name__ == "__main__":
    verificar_expiracoes()