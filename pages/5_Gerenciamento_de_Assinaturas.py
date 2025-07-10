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
# Importando as funções necessárias dos locais corretos
from auth import carregar_assinaturas, salvar_assinaturas
from utils import excluir_arquivo_do_github

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

# --- Configurações ---
EMAIL_REMETENTE = st.secrets.get("GMAIL_USER", os.getenv("GMAIL_USER"))
SENHA_APP = st.secrets.get("GMAIL_APP_PASSWORD", os.getenv("GMAIL_APP_PASSWORD"))
EMAIL_ADMIN = st.secrets.get("EMAIL_ADMIN", os.getenv("EMAIL_ADMIN"))



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

st.subheader("➕ Adicionar Nova Assinatura")
with st.form("form_nova_assinatura", clear_on_submit=True):
    novo_usuario = st.text_input("Usuário")
    nova_senha = st.text_input("Senha", type="password")
    novo_email = st.text_input("E-mail do cliente")
    sem_limite = st.checkbox("✅ Assinatura sem limite de expiração (vitalícia)")
    dias = st.number_input("Duração da assinatura (dias)", value=30, min_value=0, disabled=sem_limite)
    notificar_cliente_novo = st.checkbox("📧 Notificar cliente sobre expiração?", value=True, disabled=sem_limite)
    
    submitted = st.form_submit_button("Adicionar Assinatura")
    if submitted:
        if novo_usuario and nova_senha and novo_email:
            if novo_usuario in assinaturas:
                st.error(f"Usuário '{novo_usuario}' já existe.")
            else:
                ativacao = datetime.now()
                ativacao_str = ativacao.strftime("%Y-%m-%d %H:%M:%S")

                if sem_limite:
                    expiracao_str = "9999-12-31 23:59:59"
                else:
                    expiracao = ativacao + timedelta(days=int(dias))
                    expiracao_str = expiracao.strftime("%Y-%m-%d %H:%M:%S")

                senha_bytes = nova_senha.encode('utf-8')
                hash_da_senha = bcrypt.hashpw(senha_bytes, bcrypt.gensalt())
                
                assinaturas[novo_usuario] = {
                    "senha": hash_da_senha.decode('utf-8'),
                    "ativacao": ativacao_str,
                    "expiracao": expiracao_str,
                    "email": novo_email,
                    "email_enviado": False,
                    "notificar_cliente": notificar_cliente_novo if not sem_limite else False,
                    "primeiro_login": True, 
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

if assinaturas:
    for user, dados in list(assinaturas.items()):
        expiracao = datetime.strptime(dados['expiracao'], "%Y-%m-%d %H:%M:%S")

        with st.container(border=True):
            st.markdown(f"#### 👤 `{user}`")

            with st.popover(f"📝 Editar {user}", use_container_width=True):
                with st.form(f"form_editar_{user}"):
                    # ... (código do formulário de edição, que já estava correto) ...
                    st.write(f"Editando dados de **{user}**")
                    nova_senha_ed = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password", key=f"senha_ed_{user}")
                    novo_email_ed = st.text_input("Novo E-mail", value=dados['email'], key=f"email_ed_{user}")
                    notificar_cliente_ed = st.checkbox("Notificar cliente?", value=dados.get("notificar_cliente", True), key=f"notificar_ed_{user}")
                    if st.form_submit_button("Salvar Alterações"):
                        if nova_senha_ed:
                            senha_bytes_ed = nova_senha_ed.encode('utf-8')
                            hash_senha_ed = bcrypt.hashpw(senha_bytes_ed, bcrypt.gensalt())
                            assinaturas[user]['senha'] = hash_senha_ed.decode('utf-8')
                            assinaturas[user]['primeiro_login'] = False
                            st.success("Senha atualizada com sucesso!")
                        assinaturas[user]['email'] = novo_email_ed
                        assinaturas[user]['notificar_cliente'] = notificar_cliente_ed
                        salvar_assinaturas(assinaturas)
                        st.success("Alterações salvas.")
                        st.rerun()

            st.text(f"E-mail: {dados['email']}")
            st.text(f"Expira em: {dados['expiracao']}")
            notificacao_status = "Ativada" if dados.get("notificar_cliente", True) else "Desativada"
            st.text(f"Notificação para cliente: {notificacao_status}")
            st.text(f"Status Primeiro Login: {'Sim' if dados.get('primeiro_login', False) else 'Não'}")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"🔁 Renovar (+30d)", key=f"renovar_{user}", use_container_width=True):
                    # ... (código de renovação, que já estava correto) ...
                    data_base = expiracao if expiracao > agora else agora
                    nova_data = data_base + timedelta(days=30)
                    assinaturas[user]['expiracao'] = nova_data.strftime("%Y-%m-%d %H:%M:%S")
                    assinaturas[user]['email_enviado'] = False
                    salvar_assinaturas(assinaturas)
                    st.success(f"Assinatura de '{user}' renovada.")
                    st.rerun()

            with col2:
                if st.button(f"🔑 Forçar Nova Senha", key=f"forcar_senha_{user}", use_container_width=True):
                    # ... (código para forçar senha, que já estava correto) ...
                    assinaturas[user]['primeiro_login'] = True
                    salvar_assinaturas(assinaturas)
                    st.info(f"Usuário '{user}' será solicitado a criar nova senha no próximo login.")
                    st.rerun()

            # CORRIGIDO: Bloco 'with col3' movido para a indentação correta, dentro do 'for loop'.
            with col3:
                with st.popover(f"🗑️ Excluir", use_container_width=True):
                    st.warning(f"Tem certeza que deseja excluir '{user}' e TODOS os seus dados?")
                    
                    if st.button(f"✅ Sim, Excluir Definitivamente!", key=f"confirm_delete_final_{user}", type="primary"):
                        if user in assinaturas:
                            del assinaturas[user]
                            salvar_assinaturas(assinaturas)

                            # --- EXCLUIR ARQUIVOS DE DADOS DO USUÁRIO NO GITHUB ---
                            chat_path = f"dados/chats_historico_{user}.json"
                            preferences_path = f"preferencias/prefs_{user}.json"
                            reminders_path = f"dados/lembretes/lembretes_{user}.json"

                            excluir_arquivo_do_github(chat_path, f"Admin excluiu chat de {user}")
                            st.info(f"Solicitação para excluir chat de '{user}' enviada.")
                            
                            excluir_arquivo_do_github(preferences_path, f"Admin excluiu preferencias de {user}")
                            st.info(f"Solicitação para excluir preferências de '{user}' enviada.")
                            excluir_arquivo_do_github(reminders_path, f"Admin excluiu lembretes de {user}")
                            st.info(f"Solicitação para excluir lembretes de '{user}' enviada.")

                            st.success(f"Usuário '{user}' e seus dados foram excluídos com sucesso.")
                            st.rerun()
                    
                    if st.button("Cancelar", key=f"cancel_delete_{user}"):
                        st.info("Exclusão cancelada.")

            # CORRIGIDO: Lógica de notificação movida para a indentação correta, dentro do 'for loop'.
            if agora >= expiracao and not dados.get("email_enviado", False):
                assunto_admin = f"ALERTA: Assinatura de '{user}' Expirou"
                mensagem_admin = f"A assinatura do usuário '{user}' (email: {dados['email']}) expirou em {dados['expiracao']}."
                if EMAIL_ADMIN:
                    enviar_email(EMAIL_ADMIN, assunto_admin, mensagem_admin)

                if dados.get("notificar_cliente", True):
                    assunto_cliente = "🔔 Sua assinatura da Jarvis IA expirou"
                    mensagem_cliente = f"Olá {user},\n\nSua assinatura da Jarvis IA expirou em {expiracao.strftime('%d/%m/%Y')}. Renove para manter seu acesso."
                    enviar_email(dados["email"], assunto_cliente, mensagem_cliente)

                assinaturas[user]["email_enviado"] = True
                salvar_assinaturas(assinaturas)
                st.info(f"Notificação de expiração processada para {user}.")
else:
    st.info("Nenhuma assinatura encontrada.")

st.divider()

# --- PAINEL TURBINADO (código mantido como estava, já era funcional) ---
st.subheader("📊 Painel de Assinaturas")
# ... (o resto do seu código do painel continua aqui) ...
ativas, expiradas = [], []
for user, dados in assinaturas.items():
    expiracao = datetime.strptime(dados['expiracao'], "%Y-%m-%d %H:%M:%S")
    status = "Ativa" if expiracao > agora else "Expirada"
    entrada = {
        "Usuário": user, "Email": dados["email"], "Ativação": dados["ativacao"],
        "Expiração": dados["expiracao"], "Status": status
    }
    if status == "Ativa":
        ativas.append(entrada)
    else:
        expiradas.append(entrada)

filtro_nome = st.text_input("🔎 Filtrar por nome de usuário:")

def aplicar_filtro(lista):
    return [a for a in lista if filtro_nome.lower() in a["Usuário"].lower()] if filtro_nome else lista

def ordenar_por_data(lista):
    return sorted(lista, key=lambda x: datetime.strptime(x["Expiração"], "%Y-%m-%d %H:%M:%S"))

ativas_filtradas = ordenar_por_data(aplicar_filtro(ativas))
expiradas_filtradas = ordenar_por_data(aplicar_filtro(expiradas))

st.markdown("### ✅ Assinaturas Ativas")
if ativas_filtradas:
    df_ativas = pd.DataFrame(ativas_filtradas)
    st.dataframe(df_ativas, use_container_width=True, hide_index=True)
    csv_ativas = df_ativas.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar Ativas (.csv)", csv_ativas, "assinaturas_ativas.csv", "text/csv")
else:
    st.info("Nenhuma assinatura ativa no momento.")

st.markdown("### ❌ Assinaturas Expiradas")
if expiradas_filtradas:
    df_expiradas = pd.DataFrame(expiradas_filtradas)
    st.dataframe(df_expiradas, use_container_width=True, hide_index=True)
    csv_expiradas = df_expiradas.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar Expiradas (.csv)", csv_expiradas, "assinaturas_expiradas.csv", "text/csv")
else:
    st.success("Nenhuma assinatura expirada! 👏")