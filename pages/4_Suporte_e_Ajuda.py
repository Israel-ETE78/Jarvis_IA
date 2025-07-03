import streamlit as st

# Configuração da página
st.set_page_config(page_title="Suporte - Jarvis IA", page_icon="💡")

# --- Botão discreto para voltar ao chat principal ---
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.switch_page("app.py")

# --- Conteúdo da Página ---

st.title("💡 Central de Ajuda e Suporte do Jarvis")

st.markdown("""
Bem-vindo à Central de Ajuda! Aqui você encontrará um guia rápido sobre os comandos e funcionalidades do Jarvis.
""")

# --- Seção de Comandos ---
st.header("⚡ Comandos Rápidos")
st.markdown("""
Use estes comandos na caixa de chat para acionar ações especiais:
""")

st.info("""
**`/imagine [descrição]`**
* **O que faz:** Gera uma imagem com DALL-E 3 a partir da sua descrição.
* **Exemplo:** `/imagine um gato astronauta no estilo de van gogh`
""")

st.info("""
**`/pdf [tópico]`**
* **O que faz:** Cria um documento PDF bem formatado sobre qualquer tópico.
* **Exemplo:** `/pdf a história da inteligência artificial`
""")

st.info("""
**`/raiox`**
* **O que faz:** Executa uma análise exploratória completa (Raio-X) em um arquivo de dados (`.csv`, `.xlsx`) que você tenha carregado.
* **Requisito:** Requer que um arquivo de dados esteja no "Modo de Análise de Dados".
""")

st.info("""
**`/lembrese [informação]`**
* **O que faz:** Salva uma preferência sua na memória de longo prazo do Jarvis.
* **Exemplo:** `/lembrese meu time de futebol é o Sport Club do Recife`
""")

# --- Seção de Perguntas Frequentes ---
st.header("❔ Perguntas Frequentes (FAQ)")

with st.expander("Como funciona a Análise de Dados?"):
    st.markdown("""
    1.  Na `sidebar`, em "Anexar Arquivos", carregue um arquivo `.csv` ou `.xlsx`.
    2.  O Jarvis entrará automaticamente no "Modo de Análise de Dados".
    3.  Você pode então fazer perguntas em linguagem natural sobre os dados (ex: "qual a média de idade?") ou usar o comando `/raiox` para um resumo completo.
    4.  Para sair do modo, clique no botão "Sair do Modo de Análise" ou inicie um novo chat.
    """)

with st.expander("Como funciona a Análise de Documentos?"):
    st.markdown("""
    1.  Carregue um arquivo de texto como `.pdf`, `.docx`, ou `.txt`.
    2.  O Jarvis entrará no "Modo de Análise de Documento" e usará o conteúdo do arquivo como contexto principal para as suas perguntas.
    3.  Faça perguntas sobre o conteúdo do documento para receber respostas baseadas nele.
    """)

with st.expander("Por que o microfone não funciona na versão web?"):
    st.markdown("""
    A funcionalidade de microfone requer acesso direto ao hardware do computador, o que não é permitido por padrão em aplicativos web por razões de segurança e compatibilidade técnica. Portanto, o botão do microfone é intencionalmente desativado na versão online para evitar erros e só funciona quando você roda o Jarvis no seu computador local.
    """)

# --- Seção de Contato ---
st.header("📫 Contato")
st.markdown("""
Encontrou um bug ou tem alguma sugestão para o Jarvis? Ficarei feliz em ouvir de você.

**Para entrar em contato diretamente, envie um e-mail para:**
`jarvisiasuporte@gmail.com`
""")


# --- Fim da página ---
st.divider()
st.write("Jarvis IA - Seu Assistente Pessoal")