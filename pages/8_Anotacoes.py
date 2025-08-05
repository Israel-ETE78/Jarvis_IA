import streamlit as st
from datetime import datetime
import time

# Importando as funções de autenticação e utils
from auth import check_password
from utils import carregar_anotacoes, salvar_anotacoes

# --- 1. VERIFICAÇÃO DE LOGIN ---
# Garante que apenas usuários logados possam ver a página
if not check_password():
    st.stop()

# --- 2. CONFIGURAÇÃO DA PÁGINA E CARREGAMENTO DE DADOS ---
st.set_page_config(page_title="Minhas Anotações", layout="wide", page_icon="🗒️")

# Botão de voltar para o chat principal
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.switch_page("app.py")

st.title("🗒️ Minhas Anotações Pessoais")
st.markdown("Crie, edite e gerencie suas notas. Elas são salvas de forma segura e criptografada.")

username = st.session_state.get("username")
anotacoes = carregar_anotacoes(username)

# --- 3. INTERFACE PARA CRIAR NOVA ANOTAÇÃO ---
with st.expander("➕ Adicionar Nova Anotação", expanded=True):
    with st.form("nova_anotacao_form", clear_on_submit=True):
        novo_titulo = st.text_input("Título da Anotação")
        novo_conteudo = st.text_area("Conteúdo", height=250)
        submitted = st.form_submit_button("Salvar Anotação")

        if submitted:
            if novo_titulo and novo_conteudo:
                # Gera um ID único para a nota usando o timestamp
                note_id = str(int(time.time() * 1000))
                anotacoes[note_id] = {
                    "titulo": novo_titulo,
                    "conteudo": novo_conteudo,
                    "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                if salvar_anotacoes(anotacoes, username):
                    st.success(f"Anotação '{novo_titulo}' salva com sucesso!")
                    st.rerun()
                else:
                    st.error("Ocorreu um erro ao salvar a anotação.")
            else:
                st.warning("Por favor, preencha o título e o conteúdo da anotação.")

st.divider()

# --- 4. EXIBIÇÃO E GERENCIAMENTO DAS ANOTAÇÕES EXISTENTES ---
st.subheader("📝 Suas Anotações Salvas")

if not anotacoes:
    st.info("Você ainda não tem nenhuma anotação salva.")
else:
    # Ordena as anotações da mais recente para a mais antiga
    sorted_notes = sorted(anotacoes.items(), key=lambda item: item[1].get('data_criacao', '0'), reverse=True)
    
    for note_id, note_data in sorted_notes:
        with st.container(border=True):
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                st.markdown(f"#### {note_data.get('titulo', 'Sem Título')}")
                st.caption(f"Criado em: {note_data.get('data_criacao', 'Data desconhecida')}")
            
            with col2:
                # Popover para as opções de editar e excluir
                with st.popover("Opções ⚙️", use_container_width=True):
                    # Download da anotação como .txt
                    st.download_button(
                        label="📥 Baixar (.txt)",
                        data=note_data.get('conteudo', '').encode('utf-8'),
                        file_name=f"{note_data.get('titulo', 'anotacao').replace(' ', '_')}.txt",
                        mime="text/plain",
                        key=f"download_{note_id}",
                        use_container_width=True
                    )

                    # Exclusão da anotação
                    if st.button("🗑️ Excluir", key=f"delete_{note_id}", use_container_width=True, type="primary"):
                        # Remove a anotação do dicionário
                        anotacoes.pop(note_id, None)
                        if salvar_anotacoes(anotacoes, username):
                            st.toast(f"Anotação '{note_data.get('titulo')}' excluída.")
                            st.rerun()
                        else:
                            st.error("Erro ao excluir a anotação.")

            # Expander para ver e editar o conteúdo
            with st.expander("Ver / Editar Conteúdo"):
                with st.form(key=f"edit_form_{note_id}"):
                    conteudo_editado = st.text_area(
                        "Conteúdo",
                        value=note_data.get('conteudo', ''),
                        height=200,
                        key=f"content_edit_{note_id}"
                    )
                    if st.form_submit_button("Salvar Alterações"):
                        anotacoes[note_id]['conteudo'] = conteudo_editado
                        if salvar_anotacoes(anotacoes, username):
                            st.success("Anotação atualizada com sucesso!")
                            st.rerun()
                        else:
                            st.error("Erro ao salvar as alterações.")