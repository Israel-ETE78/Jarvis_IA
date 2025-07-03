import streamlit as st
import json
import os
from auth import check_password

# pages/1_Gerenciar_Memoria.py
import streamlit as st
from auth_admin_pages import require_admin_access # Import the new function

# === IMPORTANT: Apply the admin access check at the very beginning ===
require_admin_access()

# --- Botão de voltar para o chat principal ---
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.switch_page("app.py")

st.title("Gerenciador da Memória de Longo Prazo")
st.write("Conteúdo exclusivo para administradores da memória.")

# ... rest of your existing code for managing long-term memory ...
# (e.g., joblib.load, displaying memory content, forms for adding/editing)

# --- VERIFICAÇÃO DE LOGIN ---
if not check_password():
    st.stop() # Interrompe a execução do script se o login falhar

# --- Funções de Memória ---

def carregar_memoria():
    """Carrega a memória de um arquivo JSON."""
    try:
        with open("memoria_jarvis.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def salvar_memoria(memoria):
    """Salva a memória em um arquivo JSON."""
    with open("memoria_jarvis.json", "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=4)

# --- Callbacks para Edição em Tempo Real ---

def update_pergunta(categoria, index):
    """Callback para atualizar apenas a pergunta de um item."""
    key = f"pergunta_{categoria}_{index}"
    if categoria in st.session_state.memoria_editada and index < len(st.session_state.memoria_editada[categoria]):
        st.session_state.memoria_editada[categoria][index]['pergunta'] = st.session_state[key]

def update_respostas_multi(categoria, index):
    """Callback para atualizar a lista de respostas a partir de um text_area multilinha."""
    key = f"respostas_{categoria}_{index}"
    if categoria in st.session_state.memoria_editada and index < len(st.session_state.memoria_editada[categoria]):
        texto_completo = st.session_state[key]
        lista_respostas_novas = [resp.strip() for resp in texto_completo.strip().split('\n') if resp.strip()]
        
        if not lista_respostas_novas:
            respostas_formatadas = [{"texto": "", "tom": "neutro"}]
        else:
            respostas_formatadas = [{"texto": r, "tom": "neutro"} for r in lista_respostas_novas]
        
        st.session_state.memoria_editada[categoria][index]['respostas'] = respostas_formatadas

# --- Interface da Página de Gerenciamento ---

st.set_page_config(page_title="Gerenciador de Memória - Jarvis", layout="wide")

st.title("🧠 Gerenciador da Memória de Longo Prazo")
st.write("Aqui você pode visualizar, editar, apagar e adicionar novas memórias para o Jarvis.")

# --- LÓGICA DE ESTADO DA SESSÃO ---
if "memoria_editada" not in st.session_state:
    st.session_state.memoria_editada = carregar_memoria()

# CORREÇÃO: Inicializa a lista de exclusão segura
if "indices_para_remover" not in st.session_state:
    st.session_state.indices_para_remover = []

# CORREÇÃO: Processa as exclusões pendentes de forma segura no início da página
if st.session_state.indices_para_remover:
    for cat, idx in sorted(st.session_state.indices_para_remover, reverse=True):
        if cat in st.session_state.memoria_editada and idx < len(st.session_state.memoria_editada[cat]):
            del st.session_state.memoria_editada[cat][idx]
            if not st.session_state.memoria_editada[cat]:
                del st.session_state.memoria_editada[cat]
    
    st.session_state.indices_para_remover = [] # Limpa a lista de pendências
    st.success("Item removido da sessão de edição. Salve as alterações para confirmar.")
    st.rerun() # Rerun para garantir que a interface seja redesenhada corretamente

# --- SEÇÃO PARA ADICIONAR NOVA MEMÓRIA ---
with st.expander("➕ Adicionar Nova Memória Manualmente"):
    # (O código para adicionar nova memória permanece o mesmo, está correto)
    with st.form("nova_memoria_form", clear_on_submit=True):
        st.subheader("Preencha os dados da nova memória")
        nova_pergunta = st.text_input("Nova Pergunta Principal:")
        categorias_existentes = list(st.session_state.memoria_editada.keys())
        opcao_nova_categoria = "-- CRIAR NOVA CATEGORIA --"
        selecao_categoria = st.selectbox("Escolha uma Categoria ou Crie uma Nova:", options=categorias_existentes + [opcao_nova_categoria])
        nome_nova_categoria = ""
        if selecao_categoria == opcao_nova_categoria:
            nome_nova_categoria = st.text_input("Nome da Nova Categoria:")
        respostas_variadas = st.text_area("Respostas (uma por linha para variações):", height=150, help="Digite cada variação de resposta em uma nova linha.")
        submitted = st.form_submit_button("Adicionar à Memória")
        if submitted:
            categoria_final = nome_nova_categoria.strip().lower() if nome_nova_categoria else selecao_categoria
            if not nova_pergunta or not categoria_final or not respostas_variadas:
                st.error("Por favor, preencha todos os campos: Pergunta, Categoria e pelo menos uma Resposta.")
            else:
                lista_respostas = [resp.strip() for resp in respostas_variadas.strip().split('\n') if resp.strip()]
                novo_item = {"pergunta": nova_pergunta.strip(), "respostas": [{"texto": r, "tom": "neutro"} for r in lista_respostas]}
                if categoria_final not in st.session_state.memoria_editada:
                    st.session_state.memoria_editada[categoria_final] = []
                st.session_state.memoria_editada[categoria_final].append(novo_item)
                st.success(f"Nova memória adicionada! Clique em 'Salvar Todas as Alterações' para persistir.")
                st.rerun()

st.markdown("---")

# --- EXIBIÇÃO DA MEMÓRIA EDITÁVEL ---
if not st.session_state.memoria_editada:
    st.warning("A memória de longo prazo está vazia.")
else:
    for categoria, perguntas in list(st.session_state.memoria_editada.items()):
        if not perguntas: continue
        st.subheader(f"Categoria: {categoria.capitalize()}")
        for i, item in enumerate(perguntas):
            expander_title = item.get('pergunta', f'Item {i+1} sem pergunta')
            with st.expander(f"{expander_title}"):
                st.text_input("Pergunta:", value=item.get('pergunta', ''), key=f"pergunta_{categoria}_{i}", on_change=update_pergunta, args=(categoria, i))
                respostas_existentes = [r['texto'] for r in item.get('respostas', [])]
                texto_para_textarea = "\n".join(respostas_existentes)
                st.text_area("Respostas (uma por linha):", value=texto_para_textarea, key=f"respostas_{categoria}_{i}", height=150, on_change=update_respostas_multi, args=(categoria, i))
                
                # CORREÇÃO: O botão agora usa a lista de exclusão segura na sessão
                if st.button("Apagar esta memória", key=f"del_{categoria}_{i}"):
                    st.session_state.indices_para_remover.append((categoria, i))
                    st.rerun()

    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Salvar Todas as Alterações", type="primary", use_container_width=True):
            salvar_memoria(st.session_state.memoria_editada)
            st.success("Memória de longo prazo atualizada com sucesso!")
            st.balloons()
    with col2:
        delete_popover = st.popover("Apagar Toda a Memória", use_container_width=True)
        with delete_popover:
            st.warning("⚠️ Atenção! Esta ação é irreversível.")
            st.write("Todos os dados da memória de longo prazo serão perdidos.")
            if st.button("Confirmar Exclusão Total", type="primary", use_container_width=True):
                st.session_state.memoria_editada = {}
                salvar_memoria({})
                st.rerun()