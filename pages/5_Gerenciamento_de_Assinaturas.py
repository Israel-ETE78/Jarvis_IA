# pages/5_Gerenciamento_de_Assinaturas.py (ou o nome que você deu ao arquivo)

import streamlit as st
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
import bcrypt

# Carregar .env local se estiver rodando localmente
load_dotenv()

# Verifica o usuário logado e protege a página
ADMIN_USERNAME = st.secrets.get("ADMIN_USERNAME", os.getenv("ADMIN_USERNAME"))
username = st.session_state.get("username")

if username != ADMIN_USERNAME:
    st.error("⛔ Acesso restrito! Esta página é exclusiva para o administrador.")
    st.stop()
    
    # --- Botão de voltar para o chat principal ---
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.switch_page("app.py")

# --- Configurações e Funções Auxiliares ---
CAMINHO_ARQUIVO = "dados/assinaturas.json"
EMAIL_REMETENTE = st.secrets.get("GMAIL_USER", os.getenv("GMAIL_USER"))
SENHA_APP = st.secrets.get("GMAIL_APP_PASSWORD", os.getenv("GMAIL_APP_PASSWORD"))
EMAIL_ADMIN = st.secrets.get("EMAIL_ADMIN", os.getenv("EMAIL_ADMIN"))

def carregar_assinaturas():
    if os.path.exists(CAMINHO_ARQUIVO):
        with open(CAMINHO_ARQUIVO, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}

def salvar_assinaturas(data):
    Path("dados").mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_ARQUIVO, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def enviar_email(destinatario, assunto, mensagem):
    try:
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = destinatario
        msg.set_content(mensagem)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_REMETENTE, SENHA_APP)
            smtp.send_message(msg)
    except Exception as e:
        st.error(f"❌ Erro ao enviar e-mail para {destinatario}: {e}")

# --- Interface Principal ---
st.title("📋 Gerenciador de Assinaturas - Jarvis IA")
assinaturas = carregar_assinaturas()

# Em pages/5_Gerenciamento_de_Assinaturas.py

st.subheader("➕ Adicionar Nova Assinatura")
with st.form("form_nova_assinatura", clear_on_submit=True):
    novo_usuario = st.text_input("Usuário")
    nova_senha = st.text_input("Senha", type="password")
    novo_email = st.text_input("E-mail do cliente")

    # --- LÓGICA ATUALIZADA PARA EXPIRAÇÃO ---
    sem_limite = st.checkbox("✅ Assinatura sem limite de expiração (vitalícia)")
    
    # O campo de dias fica desativado se a opção "sem_limite" for marcada
    dias = st.number_input(
        "Duração da assinatura (dias)", 
        value=30, 
        min_value=0, 
        disabled=sem_limite
    )
    
    notificar_cliente_novo = st.checkbox("📧 Notificar cliente sobre expiração?", value=True, disabled=sem_limite)
    
    submitted = st.form_submit_button("Adicionar Assinatura")
    if submitted:
        if novo_usuario and nova_senha and novo_email:
            if novo_usuario in assinaturas:
                st.error(f"Usuário '{novo_usuario}' já existe.")
            else:
                ativacao = datetime.now()
                ativacao_str = ativacao.strftime("%Y-%m-%d %H:%M:%S")

                # Define a data de expiração com base na seleção do checkbox
                if sem_limite:
                    expiracao_str = "9999-12-31 23:59:59"
                else:
                    expiracao = ativacao + timedelta(days=int(dias))
                    expiracao_str = expiracao.strftime("%Y-%m-%d %H:%M:%S")

                # Lógica de hashing da senha
                senha_bytes = nova_senha.encode('utf-8')
                hash_da_senha = bcrypt.hashpw(senha_bytes, bcrypt.gensalt())
                
                assinaturas[novo_usuario] = {
                    "senha": hash_da_senha.decode('utf-8'),
                    "ativacao": ativacao_str,
                    "expiracao": expiracao_str,
                    "email": novo_email,
                    "email_enviado": False,
                    "notificar_cliente": notificar_cliente_novo if not sem_limite else False
                }
                salvar_assinaturas(assinaturas)
                st.success(f"✅ Assinatura para '{novo_usuario}' adicionada.")
                st.rerun()
        else:
            st.warning("⚠️ Preencha todos os campos obrigatórios.")

st.divider()

# --- Exibir e Gerenciar Assinaturas ---
st.subheader("📄 Assinaturas Atuais")
agora = datetime.now()

for user, dados in list(assinaturas.items()):
    expiracao = datetime.strptime(dados['expiracao'], "%Y-%m-%d %H:%M:%S")
    
    with st.container(border=True):
        st.markdown(f"#### 👤 `{user}`")
        
        # --- Seção de Edição (Usa um popover para não poluir a tela) ---
        with st.popover(f"📝 Editar {user}", use_container_width=True):
            with st.form(f"form_editar_{user}"):
                st.write(f"Editando dados de **{user}**")
                
                # Para edição de senha, o campo começa vazio por segurança
                nova_senha_ed = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password", key=f"senha_ed_{user}")
                novo_email_ed = st.text_input("Novo E-mail", value=dados['email'], key=f"email_ed_{user}")
                notificar_cliente_ed = st.checkbox("Notificar cliente?", value=dados.get("notificar_cliente", True), key=f"notificar_ed_{user}")

                if st.form_submit_button("Salvar Alterações"):
                    # Atualiza a senha apenas se uma nova foi digitada
                    if nova_senha_ed:
                        senha_bytes_ed = nova_senha_ed.encode('utf-8')
                        hash_senha_ed = bcrypt.hashpw(senha_bytes_ed, bcrypt.gensalt())
                        assinaturas[user]['senha'] = hash_senha_ed.decode('utf-8')
                        st.success("Senha atualizada com sucesso!")

                    # Atualiza os outros campos
                    assinaturas[user]['email'] = novo_email_ed
                    assinaturas[user]['notificar_cliente'] = notificar_cliente_ed
                    
                    salvar_assinaturas(assinaturas)
                    st.success("Alterações salvas.")
                    st.rerun()

        # --- Seção de Informações ---
        st.text(f"E-mail: {dados['email']}")
        st.text(f"Expira em: {dados['expiracao']}")
        notificacao_status = "Ativada" if dados.get("notificar_cliente", True) else "Desativada"
        st.text(f"Notificação para cliente: {notificacao_status}")

        # --- Botões de Ação Rápida ---
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"🔁 Renovar (+30d)", key=f"renovar_{user}", use_container_width=True):
                data_base = expiracao if expiracao > agora else agora
                nova_data = data_base + timedelta(days=30)
                assinaturas[user]['expiracao'] = nova_data.strftime("%Y-%m-%d %H:%M:%S")
                assinaturas[user]['email_enviado'] = False # Permite nova notificação
                salvar_assinaturas(assinaturas)
                st.success(f"Assinatura de '{user}' renovada.")
                st.rerun()
        
        with col2:
            if st.button(f"❌ Remover", key=f"remover_{user}", type="primary", use_container_width=True):
                del assinaturas[user]
                salvar_assinaturas(assinaturas)
                st.success(f"Assinatura de '{user}' removida.")
                st.rerun()
        
        # --- Lógica de Notificação Atualizada ---
        if agora >= expiracao and not dados.get("email_enviado", False):
            # [NOVA ADIÇÃO] Notifica o admin
            assunto_admin = f"ALERTA: Assinatura de '{user}' Expirou"
            mensagem_admin = f"A assinatura do usuário '{user}' (email: {dados['email']}) expirou em {dados['expiracao']}."
            if EMAIL_ADMIN:
                enviar_email(EMAIL_ADMIN, assunto_admin, mensagem_admin)

            # [NOVA ADIÇÃO] Notifica o cliente, se a opção estiver ativa
            if dados.get("notificar_cliente", True):
                assunto_cliente = "🔔 Sua assinatura da Jarvis IA expirou"
                mensagem_cliente = f"Olá {user},\n\nSua assinatura da Jarvis IA expirou em {expiracao.strftime('%d/%m/%Y')}. Renove para manter seu acesso."
                enviar_email(dados["email"], assunto_cliente, mensagem_cliente)

            assinaturas[user]["email_enviado"] = True
            salvar_assinaturas(assinaturas)
            st.info(f"Notificação de expiração processada para {user}.")


st.divider()

# --- PAINEL TURBINADO ---
st.subheader("📊 Painel de Assinaturas")

# ... (Seu código do painel turbinado continua aqui, ele não precisa de alterações) ...
# ... (Ele já usa a variável 'agora' definida anteriormente) ...

# 🔁 Reclassificar assinaturas
ativas, expiradas = [], []
for user, dados in assinaturas.items():
    expiracao = datetime.strptime(dados['expiracao'], "%Y-%m-%d %H:%M:%S")
    status = "Ativa" if expiracao > agora else "Expirada"
    entrada = {
        "Usuário": user,
        "Email": dados["email"],
        "Ativação": dados["ativacao"],
        "Expiração": dados["expiracao"],
        "Status": status
    }
    if status == "Ativa":
        ativas.append(entrada)
    else:
        expiradas.append(entrada)

# 🔍 Campo de busca por nome
filtro_nome = st.text_input("🔎 Filtrar por nome de usuário:")

def aplicar_filtro(lista):
    return [a for a in lista if filtro_nome.lower() in a["Usuário"].lower()] if filtro_nome else lista

def ordenar_por_data(lista):
    return sorted(lista, key=lambda x: datetime.strptime(x["Expiração"], "%Y-%m-%d %H:%M:%S"))

ativas_filtradas = ordenar_por_data(aplicar_filtro(ativas))
expiradas_filtradas = ordenar_por_data(aplicar_filtro(expiradas))

# ✅ Tabela de Ativas
st.markdown("### ✅ Assinaturas Ativas")
if ativas_filtradas:
    df_ativas = pd.DataFrame(ativas_filtradas)
    st.dataframe(df_ativas, use_container_width=True, hide_index=True)
    csv_ativas = df_ativas.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar Ativas (.csv)", csv_ativas, "assinaturas_ativas.csv", "text/csv")
else:
    st.info("Nenhuma assinatura ativa no momento.")

# ❌ Tabela de Expiradas
st.markdown("### ❌ Assinaturas Expiradas")
if expiradas_filtradas:
    df_expiradas = pd.DataFrame(expiradas_filtradas)
    st.dataframe(df_expiradas, use_container_width=True, hide_index=True)
    csv_expiradas = df_expiradas.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar Expiradas (.csv)", csv_expiradas, "assinaturas_expiradas.csv", "text/csv")
else:
    st.success("Nenhuma assinatura expirada! 👏")