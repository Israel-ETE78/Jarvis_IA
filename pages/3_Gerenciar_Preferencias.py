import streamlit as st
from auth import check_password
from utils import carregar_preferencias, salvar_preferencias

# Verificação de login
if not check_password():
    st.stop()

username = st.session_state.get("username")

if not username:
    st.error("Não foi possível identificar o usuário. Por favor, faça o login novamente.")
    st.stop()

st.set_page_config(page_title="Minhas Preferências", layout="wide")

# --- Botão de voltar para o chat principal ---
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.switch_page("app.py")

st.title(f"⚙️ Gerenciar Preferências de {username.capitalize()}")
st.write("Aqui você pode ver, editar e remover as informações que o Jarvis guardou sobre você.")

# 🔁 Carrega preferências a cada execução
preferencias = carregar_preferencias(username)

if not preferencias:
    st.info("Você ainda não tem nenhuma preferência salva. Use o comando `/lembrese` no chat para adicionar uma!")
else:
    for topico, valor in preferencias.items():
        # Cria chaves seguras para os widgets
        chave_segura = topico.replace(" ", "_").replace("ç", "c").replace("ã", "a").lower()
        key_valor = f"value_edit_{chave_segura}"
        key_delete = f"delete_btn_{chave_segura}"

        col1, col2, col3 = st.columns([0.4, 0.4, 0.2])

        with col1:
            st.text_input("Tópico", value=topico, disabled=True, key=f"topic_disp_{chave_segura}")

        with col2:
            novo_valor = st.text_input("Valor", value=valor, key=key_valor)
            if novo_valor != valor:
                preferencias[topico] = novo_valor
                salvar_preferencias(preferencias, username)
                st.toast(f"Preferência '{topico}' atualizada!", icon="💾")
                st.rerun()

        with col3:
            st.write("")
            st.write("")
            if st.button("🗑️ Excluir", key=key_delete, use_container_width=True):
                del preferencias[topico]
                salvar_preferencias(preferencias, username)
                # Limpa os widgets da sessão
                st.session_state.pop(key_valor, None)
                st.session_state.pop(f"topic_disp_{chave_segura}", None)
                st.toast(f"Preferência '{topico}' esquecida.", icon="👍")
                st.rerun()

st.divider()
st.subheader("➕ Adicionar Nova Preferência")

with st.form(key="add_pref_form", clear_on_submit=True):
    novo_topico = st.text_input("Novo Tópico (Ex: cor favorita, comida preferida...)")
    novo_valor = st.text_input("Valor (Ex: azul, pizza...)")
    submitted = st.form_submit_button("Adicionar Preferência")

    if submitted:
        if novo_topico and novo_valor:
            preferencias = carregar_preferencias(username)  # Garante dados atualizados
            preferencias[novo_topico.strip().lower()] = novo_valor.strip()
            salvar_preferencias(preferencias, username)
            st.success(f"✅ Preferência '{novo_topico}' adicionada!")
            st.rerun()
        else:
            st.warning("⚠️ Por favor, preencha todos os campos.")
