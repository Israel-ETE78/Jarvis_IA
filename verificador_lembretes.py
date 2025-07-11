import json
import os
from datetime import datetime
import logging
from cryptography.fernet import Fernet # Importe Fernet para criptografia
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# --- Carregar variáveis de ambiente (para GMAIL_USER, GMAIL_APP_PASSWORD, LEMBRETES_ENCRYPTION_KEY) ---
# Assumindo que o .env está na raiz do projeto (um nível acima do script se ele estiver na pasta 'pages' ou 'scripts')
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, os.pardir)) # Vai para o diretório pai
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path)

# --- Configuração do Logging ---
log_file = os.path.join(script_dir, 'verificador_lembretes.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
# --- Fim da Configuração do Logging ---

# --- Configuração da Criptografia ---
cipher_suite = None
try:
    chave_criptografia = os.environ.get('LEMBRETES_ENCRYPTION_KEY')
    
    if chave_criptografia:
        cipher_suite = Fernet(chave_criptografia.encode('utf-8'))
        logging.info("Chave de criptografia carregada com sucesso.")
    else:
        logging.critical("ERRO CRÍTICO: Variável de ambiente 'LEMBRETES_ENCRYPTION_KEY' não definida. Abortando.")
        exit(1) # Sai se a chave não estiver configurada (essencial para criptografia)
        
except Exception as e:
    logging.critical(f"ERRO CRÍTICO: Falha ao inicializar a chave de criptografia. Abortando. Erro: {e}")
    exit(1)

# --- Configuração de E-mail ---
EMAIL_REMETENTE = os.environ.get("GMAIL_USER")
SENHA_APP = os.environ.get("GMAIL_APP_PASSWORD")

def enviar_email(destinatario, assunto, mensagem):
    if not EMAIL_REMETENTE or not SENHA_APP:
        logging.error("Credenciais de e-mail não configuradas (GMAIL_USER ou GMAIL_APP_PASSWORD). Não é possível enviar e-mail.")
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
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao enviar e-mail para {destinatario}: {e}")
        return False

def carregar_assinaturas():
    """Carrega as assinaturas do arquivo dados/assinaturas.json."""
    # Caminho ajustado para 'dados/assinaturas.json' a partir da raiz do projeto
    caminho_assinaturas = os.path.join(project_root, 'dados', 'assinaturas.json')
    try:
        if os.path.exists(caminho_assinaturas):
            with open(caminho_assinaturas, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logging.error(f"ERRO: Arquivo de assinaturas '{caminho_assinaturas}' não encontrado.")
            return {}
    except json.JSONDecodeError as e:
        logging.error(f"ERRO: Falha ao decodificar JSON do arquivo '{caminho_assinaturas}'. Conteúdo inválido? Erro: {e}")
        return {}
    except Exception as e:
        logging.error(f"ERRO: Erro inesperado ao carregar assinaturas de '{caminho_assinaturas}'. Erro: {e}")
        return {}

def criptografar_e_salvar_lembretes(caminho_arquivo, lembretes_data):
    """Serializa, criptografa e salva os dados dos lembretes."""
    if not cipher_suite:
        logging.error("Cipher suite não inicializado. Não é possível criptografar.")
        return False
    try:
        json_string = json.dumps(lembretes_data, indent=2, ensure_ascii=False)
        dados_criptografados = cipher_suite.encrypt(json_string.encode('utf-8'))
        with open(caminho_arquivo, 'wb') as f:
            f.write(dados_criptografados)
        return True
    except Exception as e:
        logging.error(f"Erro ao criptografar e salvar '{caminho_arquivo}': {e}")
        return False

def carregar_e_descriptografar_lembretes(caminho_arquivo):
    """Carrega, descriptografa e desserializa os dados dos lembretes."""
    if not cipher_suite:
        logging.error("Cipher suite não inicializado. Não é possível descriptografar.")
        return []
    try:
        with open(caminho_arquivo, 'rb') as f:
            dados_criptografados = f.read()
        dados_json_bytes = cipher_suite.decrypt(dados_criptografados)
        return json.loads(dados_json_bytes.decode('utf-8'))
    except FileNotFoundError:
        raise # Permite que o chamador trate a FileNotFoundError especificamente
    except Exception as e:
        logging.error(f"Erro ao descriptografar ou parsear JSON de '{caminho_arquivo}'. Dados corrompidos ou chave errada? Erro: {e}")
        return []

def verificar_todos_os_lembretes():
    logging.info("Iniciando o script verificador de lembretes...")
    logging.info(f"Verificação iniciada em: {datetime.now()}")

    assinaturas_data = carregar_assinaturas()
    if not assinaturas_data:
        logging.warning("Nenhuma assinatura encontrada ou erro ao carregar assinaturas. Nenhuma verificação de lembrete será feita.")
        return

    logging.info(f"Carregadas {len(assinaturas_data)} assinaturas.")

    # Caminho ajustado para 'dados/lembretes' a partir da raiz do projeto
    pasta_lembretes_base = os.path.join(project_root, 'dados', 'lembretes')

    if not os.path.isdir(pasta_lembretes_base):
        logging.error(f"ERRO: Pasta de lembretes base '{pasta_lembretes_base}' não encontrada. Crie-a ou verifique o caminho.")
        return

    for username, dados_assinatura in assinaturas_data.items():
        email_usuario = dados_assinatura.get('email')
        notificar_cliente = dados_assinatura.get('notificar_cliente', True) # Assume True se não especificado
        
        if not email_usuario:
            logging.warning(f"AVISO: Usuário '{username}' não possui e-mail cadastrado em assinaturas.json. Pulando verificação de lembretes para este usuário.")
            continue
        
        # Filtra usuários com assinatura expirada (se não for "9999-12-31 23:59:59")
        expiracao_str = dados_assinatura.get('expiracao')
        if expiracao_str != "9999-12-31 23:59:59": # "9999-12-31 23:59:59" indica vitalícia
            try:
                expiracao_dt = datetime.strptime(expiracao_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() > expiracao_dt:
                    logging.info(f"Usuário '{username}' com assinatura expirada em {expiracao_str}. Pulando verificação de lembretes.")
                    continue
            except ValueError:
                logging.warning(f"Formato de data de expiração inválido para '{username}': '{expiracao_str}'. Tratando como expirado para segurança.")
                continue

        logging.info(f"\n--- Verificando lembretes para o usuário: '{username}' (E-mail: {email_usuario}) ---")
        
        caminho_lembretes_usuario = os.path.join(pasta_lembretes_base, f'chats_historico_{username}.json')
        
        lembretes_do_usuario = []
        try:
            lembretes_do_usuario = carregar_e_descriptografar_lembretes(caminho_lembretes_usuario)
            if not isinstance(lembretes_do_usuario, list):
                logging.error(f"O conteúdo descriptografado de '{caminho_lembretes_usuario}' não é uma lista válida. Pulando.")
                continue

        except FileNotFoundError:
            logging.info(f"Nenhum arquivo de lembretes encontrado para '{username}' em '{caminho_lembretes_usuario}'.")
            continue
        except Exception as e:
            logging.error(f"ERRO: Falha ao carregar/descriptografar lembretes de '{caminho_lembretes_usuario}'. {e}. Pulando.")
            continue
            
        lembretes_modificados = False
        
        for lembrete in lembretes_do_usuario:
            status = lembrete.get('status', '').lower()
            
            if status == 'pendente' and notificar_cliente: # Verifica se o usuário quer ser notificado
                try:
                    data_lembrete_str = lembrete.get('data_lembrete')
                    if not data_lembrete_str:
                        logging.warning(f"  -> AVISO: Lembrete sem 'data_lembrete' para '{lembrete.get('titulo', 'N/A')}', pulando.")
                        continue

                    try:
                        data_lembrete = datetime.fromisoformat(data_lembrete_str)
                    except ValueError: # Tenta formato mais antigo se fromisoformat falhar
                        data_lembrete = datetime.strptime(data_lembrete_str, '%Y-%m-%d %H:%M:%S')
                    
                    if datetime.now() >= data_lembrete:
                        logging.info(f"  -> Lembrete encontrado: '{lembrete.get('titulo', 'N/A')}'. Enviando para {email_usuario}...")
                        
                        sucesso = enviar_email(
                            destinatario=email_usuario,
                            assunto=f"⏰ Lembrete do Jarvis: {lembrete.get('titulo', 'Lembrete')}",
                            mensagem=f"Olá {username},\n\nEste é um lembrete para: {lembrete.get('titulo', 'Seu Lembrete')}\n\nDescrição: {lembrete.get('descricao', 'N/A')}\n\nData e Hora: {data_lembrete_str}\n\nAtenciosamente,\nSua Jarvis IA."
                        )
                        
                        if sucesso:
                            logging.info("  -> E-mail de lembrete enviado com sucesso!")
                            lembrete['status'] = 'enviado'
                            lembrete['notificacao_enviada'] = True # Marca que a notificação foi enviada
                            lembretes_modificados = True
                        else:
                            logging.warning("  -> FALHA AO ENVIAR E-MAIL DE LEMBRETE. (Verifique logs anteriores para detalhes)")

                except (ValueError, KeyError) as e:
                    logging.warning(f"  -> AVISO: Lembrete mal formatado ou com data inválida para '{lembrete.get('titulo', 'N/A')}', pulando. Erro: {e}")

        if lembretes_modificados:
            logging.info(f"Salvando alterações criptografadas no arquivo de lembretes de '{username}'...")
            if not criptografar_e_salvar_lembretes(caminho_lembretes_usuario, lembretes_do_usuario):
                logging.error(f"Falha ao salvar lembretes criptografados para '{username}'.")
        else:
            logging.info(f"Nenhum lembrete pendente para '{username}' ou nenhuma modificação necessária.")

if __name__ == '__main__':
    verificar_todos_os_lembretes()
    logging.info("\nVerificação de lembretes concluída para todos os usuários.")