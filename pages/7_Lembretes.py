import streamlit as st
import uuid
from datetime import datetime
from auth import check_password, carregar_assinaturas, salvar_assinaturas
from utils import carregar_lembretes, salvar_lembretes

# 1. VERIFICAÇÃO DE LOGIN: Padrão de segurança do projeto
if not check_password():
    st.stop()

username = st.session_state.get("username")

st.set_page_config(page_title="Meus Lembretes", layout="centered")
st.title("⏰ Meus Lembretes")

# --- Botão de voltar para o chat principal ---
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.switch_page("app.py")

# Carrega os lembretes do usuário logado
try:
    lembretes = carregar_lembretes(username)
except Exception as e:
    st.error(f"Ocorreu um erro ao carregar seus lembretes. Tente recarregar a página. Erro: {e}")
    lembretes = []

# --- FORMULÁRIO PARA ADICIONAR NOVO LEMBRETE ---
st.subheader("✍️ Adicionar Novo Lembrete")
with st.form("novo_lembrete_form", clear_on_submit=True):
    novo_titulo = st.text_input("Título do lembrete")
    nova_descricao = st.text_area("Descrição (opcional)")
    
    col_data, col_hora = st.columns(2)
    with col_data:
        nova_data = st.date_input("Data do Lembrete", min_value=datetime.today())
    with col_hora:
        novo_horario = st.time_input("Horário do Lembrete")

    submit_novo = st.form_submit_button("Salvar Lembrete", type="primary", use_container_width=True)

    if submit_novo:
        if not novo_titulo:
            st.warning("O título é obrigatório.")
        else:
            data_hora_lembrete = datetime.combine(nova_data, novo_horario)
            
            novo_lembrete = {
                "id": str(uuid.uuid4()),
                "titulo": novo_titulo,
                "descricao": nova_descricao,
                "data_lembrete": data_hora_lembrete.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "pendente",
                "notificacao_enviada": False,
                "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            lembretes.append(novo_lembrete)
            salvar_lembretes(username, lembretes)
            st.success(f"Lembrete '{novo_titulo}' adicionado com sucesso!")
            st.rerun()

st.divider()

# --- EXIBIR LEMBRETES EXISTENTES ---
st.subheader("🗓️ Seus Lembretes")

if not lembretes:
    st.info("Você ainda não tem nenhum lembrete cadastrado. Use o formulário acima para começar!")
else:
    # Ordena os lembretes por data (mais próximos primeiro)
    lembretes_ordenados = sorted(lembretes, key=lambda x: x['data_lembrete'])

    for lembrete in lembretes_ordenados:
        data_lembrete_dt = datetime.strptime(lembrete['data_lembrete'], "%Y-%m-%d %H:%M:%S")

        with st.container(border=True):
            col_info, col_acoes = st.columns([0.8, 0.2])
            
            with col_info:
                st.markdown(f"**{lembrete['titulo']}**")
                st.caption(f"Lembrar em: {data_lembrete_dt.strftime('%d/%m/%Y às %H:%M')}")
                if lembrete['descricao']:
                    with st.expander("Ver descrição"):
                        st.write(lembrete['descricao'])
            
            with col_acoes:
                # Botão para Editar (usando popover)
                with st.popover("✏️ Editar", use_container_width=True):
                    with st.form(f"form_edit_{lembrete['id']}"):
                        st.write(f"Editando: **{lembrete['titulo']}**")
                        titulo_edit = st.text_input("Título", value=lembrete['titulo'], key=f"titulo_{lembrete['id']}")
                        descricao_edit = st.text_area("Descrição", value=lembrete['descricao'], key=f"desc_{lembrete['id']}")
                        
                        data_edit = st.date_input("Data", value=data_lembrete_dt.date(), key=f"data_{lembrete['id']}", min_value=datetime.today())
                        hora_edit = st.time_input("Horário", value=data_lembrete_dt.time(), key=f"hora_{lembrete['id']}")
                        
                        if st.form_submit_button("Salvar Alterações", type="primary"):
                            data_hora_editada = datetime.combine(data_edit, hora_edit)
                            # Atualiza o lembrete na lista original
                            lembrete['titulo'] = titulo_edit
                            lembrete['descricao'] = descricao_edit
                            lembrete['data_lembrete'] = data_hora_editada.strftime("%Y-%m-%d %H:%M:%S")
                            lembrete['notificacao_enviada'] = False # Reseta a notificação ao editar
                            
                            salvar_lembretes(username, lembretes)
                            st.success("Lembrete atualizado!")
                            st.rerun()

                # Botão para Excluir
                if st.button("🗑️ Excluir", key=f"del_{lembrete['id']}", use_container_width=True):
                    lembretes_filtrados = [l for l in lembretes if l['id'] != lembrete['id']]
                    salvar_lembretes(username, lembretes_filtrados)
                    st.success(f"Lembrete '{lembrete['titulo']}' excluído.")
                    st.rerun()

# --- CONFIGURAÇÃO DE E-MAIL (BÔNUS) ---
# Esta seção permite que o usuário use o e-mail já cadastrado na assinatura.
st.divider()
with st.expander("⚙️ Configurações de Notificação"):
    assinaturas = carregar_assinaturas()
    dados_usuario = assinaturas.get(username)
    if dados_usuario:
        email_atual = dados_usuario.get("email")
        st.info(f"As notificações serão enviadas para o e-mail: **{email_atual}**")
        st.caption("Este e-mail é gerenciado pelo administrador na página de assinaturas.")
    else:
        st.warning("Não foi possível carregar seu e-mail de notificação.")