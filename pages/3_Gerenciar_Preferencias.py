import streamlit as st
from auth import check_password
from utils import carregar_preferencias, salvar_preferencias

# 1. ESSENCIAL: Garante que o usuário está logado para acessar esta página
if not check_password():
    st.stop()

# Pega o nome de usuário da sessão
username = st.session_state.get("username")

if not username:
    st.error("Não foi possível identificar o usuário. Por favor, faça o login novamente.")
    st.stop()

st.set_page_config(page_title="Minhas Preferências", layout="wide")
st.title(f"⚙️ Gerenciar Preferências de {username.capitalize()}")

st.write("Aqui você pode ver, editar e remover as informações que o Jarvis guardou sobre você.")

# Carrega as preferências atuais do usuário
preferencias = carregar_preferencias(username)

if not preferencias:
    st.info("Você ainda não tem nenhuma preferência salva. Use o comando `/lembrese` no chat para adicionar uma!")
else:
    # Exibe cada preferência com opções para editar e excluir
    for topico, valor in list(preferencias.items()):
        col1, col2, col3 = st.columns([0.4, 0.4, 0.2])

        with col1:
            st.text_input("Tópico", value=topico, disabled=True, key=f"topic_disp_{topico}")

        with col2:
            # O valor é editável
            novo_valor = st.text_input("Valor", value=valor, key=f"value_edit_{topico}")
            if novo_valor != valor:
                preferencias[topico] = novo_valor
                salvar_preferencias(preferencias, username)
                st.toast(f"Preferência '{topico}' atualizada!", icon="💾")
                st.rerun() # Recarrega para garantir consistência

        with col3:
            # Botão para deletar a preferência
            st.write("") # Espaçamento
            st.write("") # Espaçamento
            if st.button("🗑️ Excluir", key=f"delete_btn_{topico}", use_container_width=True):
                del preferencias[topico]
                salvar_preferencias(preferencias, username)
                st.toast(f"Preferência '{topico}' esquecida.", icon="👍")
                st.rerun()

st.divider()

# --- SEÇÃO CORRIGIDA E SIMPLIFICADA ---

st.subheader("Adicionar Nova Preferência")

# A mágica acontece aqui no parâmetro 'clear_on_submit=True'
with st.form(key="add_pref_form", clear_on_submit=True):
    novo_topico = st.text_input("Novo Tópico (Ex: cor favorita, filme preferido, etc.)")
    novo_valor_form = st.text_input("Valor (Ex: azul, O Poderoso Chefão, etc.)")
    
    submitted = st.form_submit_button("Adicionar Preferência")

    if submitted:
        if novo_topico and novo_valor_form:
            # Carrega as preferências, adiciona a nova e salva
            preferencias_atuais = carregar_preferencias(username)
            preferencias_atuais[novo_topico.lower()] = novo_valor_form
            salvar_preferencias(preferencias_atuais, username)
            st.success(f"Preferência '{novo_topico}' adicionada com sucesso!")
            # Não precisamos fazer mais nada, o rerun é implícito e o form limpará os campos.
        else:
            st.warning("Por favor, preencha tanto o tópico quanto o valor.")