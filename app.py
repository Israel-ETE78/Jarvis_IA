# ==============================================================================
# === 1. IMPORTAÇÕES DE BIBLIOTERAS (REVISADO PARA NUVEM)
# ==============================================================================
import logging
import streamlit as st
import copy
from openai import OpenAI
import json
from difflib import SequenceMatcher
import fitz  # PyMuPDF
import docx
from dotenv import load_dotenv
import os
import datetime
import random
import re
import base64
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from auth import check_password  # Sua autenticação local
from utils import carregar_preferencias, salvar_preferencias
import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import requests
import io
# As bibliotecas librosa, io (se usado apenas para áudio), soundfile, PyAudio foram removidas
# do contexto do microfone e processamento de áudio em tempo real.
from fpdf.enums import XPos, YPos
from openai import RateLimitError
import time
from supabase import create_client, Client
from pathlib import Path
from utils import encrypt_file_content_general, decrypt_file_content_general
from utils import carregar_dados_do_github, salvar_dados_no_github, decrypt_file_content_general, encrypt_file_content_general
from utils import salvar_emocoes, carregar_emocoes
from datetime import datetime


# ✅ Bloco de ping para manter o app acordado
params = st.query_params
if "ping" in params:
    st.write("✅ Jarvis IA está online!")
    st.stop()
# ==============================================================================
# === 2. VERIFICAÇÃO DE LOGIN E CONFIGURAÇÃO INICIAL
# ==============================================================================
ADMIN_USERNAME = st.secrets.get("ADMIN_USERNAME", os.getenv("ADMIN_USERNAME"))
if not ADMIN_USERNAME:
    st.error(
        "Nome de usuário admin não encontrado! Defina ADMIN_USERNAME em .env ou secrets.")
    st.stop()

# Executa a verificação de login primeiro
if not check_password():
    st.stop()  # Interrompe a execução do script se o login falhar

# --- Define visibilidade padrão do campo de feedback ---
# Ajustado para que o feedback possa ser sempre visível se desejar, ou controlado por admin
if st.session_state.get("username") != ADMIN_USERNAME:
    st.session_state["show_feedback_form"] = True
else:
    st.session_state["show_feedback_form"] = True

emocoes_dict = {} # Inicializa como dicionário vazio para evitar erros caso não carregue
ultima_emocao = None
if st.session_state.username:
    emocoes_dict_carregadas = carregar_emocoes(st.session_state.username)
    if emocoes_dict_carregadas:
        emocoes_dict = emocoes_dict_carregadas
        try:
            latest_timestamp = max(emocoes_dict.keys(), key=lambda k: datetime.fromisoformat(k))
            latest_entry = emocoes_dict[latest_timestamp]
            # --- INÍCIO DA MODIFICAÇÃO NECESSÁRIA ---
            if isinstance(latest_entry, dict):
                ultima_emocao = latest_entry.get("emocao", "neutro").lower()
            else: # Formato antigo (apenas string)
                ultima_emocao = str(latest_entry).lower()
            # --- FIM DA MODIFICAÇÃO NECESSÁRIA ---
        except Exception as e:
            print(f"Erro ao obter a última emoção carregada: {e}")
            ultima_emocao = None
# ==============================================================================
# === 3. CONEXÃO INTELIGENTE DE API (LOCAL E NUVEM)
# ==============================================================================

# Carrega as variáveis do arquivo .env (para o ambiente local)
load_dotenv()

# Verifica se a chave está nos "Secrets" do Streamlit (quando está na nuvem)
if "OPENAI_API_KEY" in st.secrets:
    # Ambiente da Nuvem
    st.sidebar.success("Jarvis Online", icon="☁️")
    api_key = st.secrets["OPENAI_API_KEY"]
    # Usamos .get() para não dar erro se não existir
    api_key_serper = st.secrets.get("SERPER_API_KEY")
else:
    # Ambiente Local
    st.sidebar.info("Jarvis Online", icon="☁️")
    api_key = os.getenv("OPENAI_API_KEY")
    api_key_serper = os.getenv("SERPER_API_KEY")

# Validação para garantir que a chave de API foi carregada
if not api_key:
    st.error(
        "Chave de API da OpenAI não encontrada! Verifique seu arquivo .env ou os Secrets na nuvem.")
    st.stop()

# Inicializa o modelo da OpenAI com a chave correta
modelo = OpenAI(api_key=api_key)


def chamar_openai_com_retries(modelo_openai, mensagens, modelo="gpt-4o", max_tentativas=3, pausa_segundos=5):
    """
    Faz a chamada à API da OpenAI com tentativas automáticas em caso de RateLimitError.
    """
    for tentativa in range(1, max_tentativas + 1):
        try:
            st.info(f"⏳ Um instante... (consulta {tentativa}) em andamento")
            resposta = modelo_openai.chat.completions.create(
                model=modelo,
                messages=mensagens
            )
            return resposta  # sucesso!
        except RateLimitError:
            st.warning(
                f"⚠️ Limite de requisições atingido. Tentando novamente em {pausa_segundos} segundos...")
            time.sleep(pausa_segundos)
        except Exception as e:
            st.error(f"❌ Erro inesperado: {e}")
            break

    st.error("❌ Tentativas esgotadas. Aguardando você tentar novamente mais tarde.")
    return None

# ==============================================================================
# === 4. CONFIGURAÇÃO DE LOGS
# ==============================================================================


def setup_logging():
    """Configura o sistema de log para registrar eventos em um arquivo."""
    logging.basicConfig(
        filename='jarvis_log.txt',
        filemode='a',  # 'a' para adicionar ao arquivo, 'w' para sobrescrever
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        encoding='utf-8'
    )


setup_logging()

# --- CARREGAR O MODELO E FERRAMENTAS ---


@st.cache_resource
def carregar_modelo_embedding():
    """Carrega o modelo de embedding que é pesado e não muda."""
    print("Executando CARGA PESADA do modelo de embedding (isso só deve aparecer uma vez)...")
    try:
        return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    except Exception as e:
        print(f"Erro fatal ao carregar o modelo de embedding: {e}")
        return None


def inicializar_memoria_dinamica():
    """Carrega os vetores e a base de conhecimento no estado da sessão, se ainda não estiverem lá."""
    if 'vetores_perguntas' not in st.session_state:
        print("Inicializando memória dinâmica na sessão...")
        try:
            st.session_state.vetores_perguntas = np.load(
                'vetores_perguntas_v2.npy')
            st.session_state.base_de_conhecimento = joblib.load(
                'dados_conhecimento_v2.joblib')
            print("Memória dinâmica carregada com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar arquivos de memória (.npy, .joblib): {e}")
            st.session_state.vetores_perguntas = None
            st.session_state.base_de_conhecimento = None


# --- CARREGAR O MODELO E INICIALIZAR A MEMÓRIA ---
modelo_embedding = carregar_modelo_embedding()
inicializar_memoria_dinamica()  # Garante que a memória está pronta na sessão

# Exibe a mensagem de status no painel lateral
if modelo_embedding:
    st.sidebar.success("Memória ativada.", icon="💾")
else:
    st.sidebar.error("Arquivos do modelo local não encontrados.")

# --- Funções do Aplicativo ---

# <--- FUNÇÃO OTIMIZADA: Substitui detectar_emocao, detectar_tom_usuario e classificar_categoria
def analisar_metadados_prompt(prompt_usuario):
    """
    Analisa o prompt do usuário com uma única chamada à IA para extrair múltiplos metadados.
    Retorna um dicionário com emoção, sentimento, categoria e tipo de interação.
    """
    if not prompt_usuario or not prompt_usuario.strip():
        return {
            "emocao": "neutro", "sentimento_usuario": "n/a",
            "categoria": "geral", "tipo_interacao": "conversa_geral"
        }

    prompt_analise = f"""
    Analise o texto do usuário e extraia as seguintes informações em um objeto JSON:
    1. "emocao": A emoção principal. Escolha uma de: 'feliz', 'triste', 'irritado', 'neutro', 'curioso', 'grato', 'ansioso', 'confuso', 'surpreso', 'animado', 'preocupado'.
    2. "sentimento_usuario": O tom ou estado de espírito em poucas palavras (ex: 'apressado', 'curioso', 'frustrado').
    3. "categoria": Uma categoria simples para o tópico (ex: 'geografia', 'programação', 'sentimentos').
    4. "tipo_interacao": Classifique como 'pergunta', 'comando', 'desabafo_apoio' ou 'conversa_geral'.

    Texto do usuário: "{prompt_usuario}"

    Responda APENAS com o objeto JSON.
    """
    try:
        # Usa um modelo mais rápido e barato para esta tarefa de classificação simples
        modelo_selecionado = 'gpt-3.5-turbo'
        resposta_modelo = modelo.chat.completions.create(
            model=modelo_selecionado,
            messages=[{"role": "user", "content": prompt_analise}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(resposta_modelo.choices[0].message.content)
    except Exception as e:
        print(f"Erro ao analisar metadados do prompt: {e}")
        # Retorna um dicionário padrão em caso de erro
        return {
            "emocao": "neutro", "sentimento_usuario": "n/a",
            "categoria": "geral", "tipo_interacao": "conversa_geral"
        }


def limpar_pdf_da_memoria():
    """Remove os dados do PDF do st.session_state para o botão de download desaparecer."""
    if 'pdf_para_download' in st.session_state:
        del st.session_state['pdf_para_download']
    if 'pdf_filename' in st.session_state:
        del st.session_state['pdf_filename']

# <--- REMOVIDO: A segunda definição duplicada de limpar_pdf_da_memoria foi apagada.

def gerar_conteudo_para_pdf(topico):
    """Usa a IA para gerar um texto bem formatado sobre um tópico para o PDF."""
    prompt = f"Por favor, escreva um texto detalhado e bem estruturado sobre o seguinte tópico para ser incluído em um documento PDF. Organize com parágrafos claros e, se apropriado, use listas. Tópico: '{topico}'"
    modelo_selecionado = st.session_state.get('admin_model_choice', 'gpt-4o')
    resposta_modelo = modelo.chat.completions.create(
        model=modelo_selecionado,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2048
    )
    return resposta_modelo.choices[0].message.content


def criar_pdf(texto_corpo, titulo_documento):
    """
    Cria um arquivo PDF em memória, interpretando formatação Markdown
    e usando uma fonte Unicode local de forma robusta e portatil.
    """
    pdf = FPDF()
    pdf.add_page()

    # Constrói o caminho completo e robusto para as fontes
    script_dir = os.path.dirname(__file__)
    font_path_regular = os.path.join(script_dir, 'assets', 'DejaVuSans.ttf')
    font_path_bold = os.path.join(script_dir, 'assets', 'DejaVuSans-Bold.ttf')

    try:
        pdf.add_font('DejaVu', '', font_path_regular)
        pdf.add_font('DejaVu', 'B', font_path_bold)
        FONT_FAMILY = 'DejaVu'
    except Exception: 
        print("AVISO: Arquivos de fonte não encontrados. Verifique a pasta 'assets'. Usando Helvetica.")
        FONT_FAMILY = 'Helvetica'

    pdf.set_font(FONT_FAMILY, 'B', 18)
    pdf.multi_cell(0, 10, titulo_documento, new_x=XPos.LMARGIN,
                   new_y=YPos.NEXT, align='C')
    pdf.ln(15)

    texto_corpo_ajustado = texto_corpo.strip().replace(
        '*\n', '* ').replace('-\n', '- ')
    linhas = texto_corpo_ajustado.split('\n')

    for linha in linhas:
        linha = linha.strip()
        if linha.startswith('### '):
            pdf.set_font(FONT_FAMILY, 'B', 14)
            pdf.multi_cell(0, 8, linha.lstrip('### ').strip(),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(4)
        elif linha.startswith('## '):
            pdf.set_font(FONT_FAMILY, 'B', 16)
            pdf.multi_cell(0, 10, linha.lstrip('## ').strip(),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(6)
        elif linha.startswith('# '):
            pdf.set_font(FONT_FAMILY, 'B', 18)
            pdf.multi_cell(0, 12, linha.lstrip('# ').strip(),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(8)
        # --- ADIÇÃO PARA CABEÇALHO H4 (####) ---
        elif linha.startswith('#### '): 
            pdf.set_font(FONT_FAMILY, 'B', 12) 
            pdf.multi_cell(0, 7, linha.lstrip('#### ').strip(),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3) 
        # --- FIM DA ADIÇÃO ---
        elif re.match(r'^\*\*(.+?)\*\*$', linha): 
            pdf.set_font(FONT_FAMILY, 'B', 12)
            texto_negrito = re.sub(r'^\*\*(.+?)\*\*$', r'\1', linha)
            pdf.multi_cell(0, 7, texto_negrito,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)
        elif linha.startswith('* ') or linha.startswith('- '):
            pdf.set_font(FONT_FAMILY, '', 12)
            bullet = "•" if FONT_FAMILY == 'DejaVu' else "*"
            pdf.cell(8, 7, f"  {bullet} ")
            texto_da_linha = linha.lstrip('* ').lstrip('- ').strip()            
            write_with_mixed_styles(texto_da_linha, pdf, FONT_FAMILY)
            pdf.ln(2)
        elif linha:
            pdf.set_font(FONT_FAMILY, '', 12)            
            write_with_mixed_styles(linha, pdf, FONT_FAMILY)
            pdf.ln(5)

    return bytes(pdf.output())


def write_with_mixed_styles(text, pdf, font_family):
    """
    Escreve uma linha de texto no PDF, alternando entre estilos normal e negrito
    com base na marcação '**'.
    """
    parts = text.split('**')
    for i, part in enumerate(parts):
        if i % 2 == 1:
            pdf.set_font(font_family, 'B')
        else:
            pdf.set_font(font_family, '')
        pdf.write(7, part)
    pdf.ln()


def extrair_texto_documento(uploaded_file):
    """Extrai o texto de arquivos PDF, DOCX, TXT, Excel, e várias linguagens de programação e scripts de banco de dados."""
    nome_arquivo = uploaded_file.name

    if nome_arquivo.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            return df.to_csv(index=False)
        except Exception as e:
            return f"Erro ao ler o arquivo Excel: {e}"
    elif nome_arquivo.endswith(".pdf"):
        texto = ""
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            for page in doc:
                texto += page.get_text()
        return texto
    elif nome_arquivo.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif nome_arquivo.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    # --- Modificação ABRANGENTE para arquivos de programação e script ---
    elif nome_arquivo.endswith((
        '.py', '.js', '.ts', '.html', '.htm', '.css', '.php', '.java', '.kt',
        '.c', '.cpp', '.h', '.cs', '.rb', '.go', '.swift', '.sql', '.json',
        '.xml', '.yaml', '.yml', '.md', '.sh', '.bat', '.ps1', '.R', '.pl', '.lua'
    )):
        try:
            # Tenta UTF-8 primeiro, que é o mais comum para código
            return uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            # Se UTF-8 falhar, tenta Latin-1 (ou outra codificação comum no seu contexto)
            return uploaded_file.read().decode("latin-1")
        except Exception as e:
            return f"Erro ao ler o arquivo de código/script: {e}"
    # --- FIM da modificação ---
    return "Formato de arquivo não suportado."

def gerar_imagem_com_dalle(prompt_para_imagem):
    """
    Gera uma imagem com DALL-E 3 e retorna seus dados em formato Base64.
    """
    try:
        st.info(
            f"🎨 Gerando imagem com DALL-E 3 para: '{prompt_para_imagem}'...")
        response = modelo.images.generate(
            model="dall-e-3",
            prompt=prompt_para_imagem,
            size="1024x1024",
            quality="standard",
            n=1
        )
        # Pega a URL temporária gerada
        image_url = response.data[0].url

        # --- NOVA LÓGICA ---
        # Baixa o conteúdo da imagem a partir da URL
        st.info("📥 Baixando dados da imagem para armazenamento permanente...")
        image_response = requests.get(image_url)
        image_response.raise_for_status()  # Verifica se o download foi bem-sucedido

        # Converte os dados da imagem para Base64
        image_base64 = base64.b64encode(image_response.content).decode('utf-8')

        st.success("Imagem gerada e armazenada com sucesso!")

        # Retorna a string Base64, e não mais a URL
        return f"data:image/png;base64,{image_base64}"

    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar a imagem: {e}")
        return None

# <--- REMOVIDAS: As funções `classificar_categoria`, `detectar_tom_emocional`, e `detectar_tom_usuario` foram substituídas pela nova `analisar_metadados_prompt`.

def detectar_idioma_com_ia(texto_usuario):
    """Usa a própria OpenAI para detectar o idioma, um método mais preciso."""
    if not texto_usuario.strip():
        return 'pt'  # Retorna português como padrão se o texto for vazio

    try:
        prompt = f"Qual o código de idioma ISO 639-1 (ex: 'en', 'pt', 'es') do seguinte texto? Responda APENAS com o código de duas letras.\n\nTexto: \"{texto_usuario}\""

        modelo_selecionado = st.session_state.get(
            'admin_model_choice', 'gpt-4o')
        resposta_modelo = modelo.chat.completions.create(
            model=modelo_selecionado,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,  # Super curto e rápido
            temperature=0
        )
        idioma = resposta_modelo.choices[0].message.content.strip().lower()

        # Garante que a resposta tenha apenas 2 caracteres
        if len(idioma) == 2:
            return idioma
        else:
            return 'pt'  # Retorna um padrão seguro em caso de resposta inesperada

    except Exception as e:
        print(f"Erro ao detectar idioma com IA: {e}")
        return 'pt'  # Retorna um padrão seguro em caso de erro


def preparar_texto_para_fala(texto):
    """
    Prepara o texto para ser falado (removendo markdown, emojis, etc.).
    Esta função é usada pelo TTS (Text-to-Speech) do navegador, que não depende de bibliotecas Python.
    """
    # Remove links mantendo apenas o texto visível
    texto = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', texto)

    # Remove emojis
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    texto = emoji_pattern.sub('', texto)

    # Remove marcações de markdown
    texto = texto.replace('**', '').replace('__', '')
    texto = texto.replace('*', '').replace('_', '')
    texto = texto.replace('~~', '').replace('```', '')

    # Remove cabeçalhos, citações e listas
    texto = re.sub(r'^\s*#+\s*', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'^\s*>\s*', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'^\s*[-*•]\s+', '', texto, flags=re.MULTILINE)

    # Substituições sutis
    texto = texto.replace(':', ',').replace('—', ',')
    texto = re.sub(r'(\d+)\.', r'\1,', texto)

    # Insere pausas claras após pontuações
    texto = re.sub(r'([.!?])\s*', r'\1 ... ', texto)

    # Pausas suaves em quebras de linha
    texto = texto.replace('\n', ' ... ')

    # Remove espaços excessivos
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto

def carregar_memoria():
    try:
        with open("memoria_jarvis.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar_memoria(memoria):
    with open("memoria_jarvis.json", "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=4)

def adicionar_a_memoria(pergunta, resposta, modelo_emb):
    """
    Adiciona um novo par de pergunta e resposta à memória dinâmica (vetores em sessão)
    e à memória persistente (arquivo JSON).
    """
    if not modelo_emb:
        st.error("O modelo de embedding não está carregado. Não é possível salvar na memória.")
        return

    try:
        # --- ETAPA 1: ATUALIZAR A MEMÓRIA EM TEMPO DE EXECUÇÃO (SESSION_STATE) ---
        st.info("Atualizando a memória dinâmica da sessão...")

        novo_vetor = modelo_emb.encode([pergunta])

        if 'vetores_perguntas' in st.session_state and st.session_state.vetores_perguntas is not None:
            st.session_state.vetores_perguntas = np.vstack(
                [st.session_state.vetores_perguntas, novo_vetor])
        else:
            st.session_state.vetores_perguntas = novo_vetor

        nova_resposta_formatada = {'texto': resposta, 'tom': 'neutro'}
        if 'base_de_conhecimento' in st.session_state and st.session_state.base_de_conhecimento is not None:
             st.session_state.base_de_conhecimento['respostas'].append(
                [nova_resposta_formatada])
        else:
            st.session_state.base_de_conhecimento = {'respostas': [[nova_resposta_formatada]]}


        st.toast("✅ Memória dinâmica atualizada para esta sessão!", icon="🧠")
        print(
            f"Novo tamanho da matriz de vetores na sessão: {st.session_state.vetores_perguntas.shape}")

        # --- ETAPA 2: PERSISTIR A MEMÓRIA NO ARQUIVO JSON ---
        memoria_persistente = carregar_memoria()
        # <--- MODIFICADO: Usa a nova função otimizada para obter a categoria
        categoria = analisar_metadados_prompt(pergunta).get('categoria', 'geral')

        nova_entrada = {
            "pergunta": pergunta,
            "respostas": [{"texto": resposta, "tom": "neutro"}]
        }

        if categoria not in memoria_persistente:
            memoria_persistente[categoria] = []

        if not any(item["pergunta"].lower() == pergunta.lower() for item in memoria_persistente[categoria]):
            memoria_persistente[categoria].append(nova_entrada)
            salvar_memoria(memoria_persistente)
            st.toast("💾 Memória também salva permanentemente no arquivo JSON.", icon="📝")
        else:
            st.toast("Essa pergunta já existe na memória permanente.", icon="💡")

    except Exception as e:
        st.error(f"Erro ao atualizar a memória: {e}")

def processar_comando_lembrese(texto_do_comando):
    """Usa a OpenAI para extrair um tópico e valor de um texto e salvar nas preferências."""
    st.info("Processando informação para minha memória de preferências...")

    prompt = f"""
    Analise a seguinte afirmação feita por um usuário: '{texto_do_comando}'.
    Sua tarefa é extrair o tópico principal e o valor associado a ele.
    Responda apenas com um objeto JSON contendo as chaves "topico" e "valor".

    Exemplos:
    - Afirmação: "meu time de futebol é o Sport Club do Recife" -> Resposta: {{"topico": "time de futebol", "valor": "Sport Club do Recife"}}
    - Afirmação: "meu aniversário é em 15 de maio" -> Resposta: {{"topico": "aniversário", "valor": "15 de maio"}}
    - Afirmação: "meu filme favorito é Interestelar" -> Resposta: {{"topico": "filme favorito", "valor": "Interestelar"}}
    """

    try:
        modelo_selecionado = st.session_state.get(
            'admin_model_choice', 'gpt-4o')
        resposta_modelo = modelo.chat.completions.create(
            model=modelo_selecionado,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        resultado_json = json.loads(resposta_modelo.choices[0].message.content)
        topico = resultado_json.get("topico")
        valor = resultado_json.get("valor")

        if topico and valor:
            username = st.session_state.get("username", "default")
            preferencias = carregar_preferencias(username)
            preferencias[topico.lower()] = valor
            salvar_preferencias(preferencias, username)
            st.toast(
                f"Entendido! Guardei que seu '{topico}' é '{valor}'.", icon="👍")
        else:
            st.warning(
                "Não consegui identificar um tópico e um valor claros para memorizar.")

    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar memorizar a preferência: {e}")


def carregar_chats(username):
    """Carrega os chats de um arquivo JSON no GitHub, descriptografando o conteúdo."""
    if not username:
        return {}

    filename = f"dados/chats_historico_{username}.json"
    encrypted_file_content = carregar_dados_do_github(filename)

    if encrypted_file_content:
        try:
            decrypted_file_content = decrypt_file_content_general(
                encrypted_file_content)
            return json.loads(decrypted_file_content)
        except Exception as e:
            print(
                f"AVISO: Falha ao descriptografar chats de '{username}' do GitHub. Tentando como JSON bruto. Erro: {e}")
            try:
                return json.loads(encrypted_file_content)
            except json.JSONDecodeError:
                print(
                    f"ERRO FATAL: Conteúdo do chat de '{username}' do GitHub não é um JSON válido.")
                return {}
    return {}


def salvar_chats(username):
    """
    Salva os chats do usuário no GitHub, ignorando objetos não-serializáveis
    e criptografando o conteúdo.
    """
    if not username or "chats" not in st.session_state:
        return

    chats_para_salvar = copy.deepcopy(st.session_state.chats)

    
    for chat_id, chat_data in chats_para_salvar.items():
        if "title" not in chat_data:
            chat_data["title"] = "Chat sem título"

    for chat_id, chat_data in chats_para_salvar.items():
        if "dataframe" in chat_data:
            del chat_data["dataframe"]
        if "messages" in chat_data:
            mensagens_serializaveis = [
                msg for msg in chat_data["messages"] if msg.get("type") != "plot"]
            chat_data["messages"] = mensagens_serializaveis

    data_json_string = json.dumps(
        chats_para_salvar, ensure_ascii=False, indent=4)
    encrypted_data_string = encrypt_file_content_general(data_json_string)

    filename = f"dados/chats_historico_{username}.json"
    mensagem_commit = f"Atualiza chat do usuario {username}"
    try:
        salvar_dados_no_github(
            filename, encrypted_data_string, mensagem_commit)
        print(f"Chats de '{username}' salvos no GitHub.")
    except Exception as e:
        print(f"Erro ao salvar chats no GitHub: {e}")



def escolher_resposta_por_contexto(entry):
    if entry["respostas"]:
        return random.choice(entry["respostas"])["texto"]
    return None


def buscar_resposta_local(pergunta_usuario, memoria, limiar=0.9):
    pergunta_usuario = pergunta_usuario.lower()
    melhor_match, melhor_score = None, 0
    for categoria in memoria:
        for item in memoria[categoria]:
            score = SequenceMatcher(
                None, pergunta_usuario, item["pergunta"].lower()).ratio()
            if score > melhor_score and score >= limiar:
                melhor_match, melhor_score = item, score
    if melhor_match:
        return escolher_resposta_por_contexto(melhor_match)
    return None

def adaptar_estilo_com_base_na_emocao(ultima_emocao):
    if not ultima_emocao:
        return ""
    if ultima_emocao in ["triste", "cansado", "preocupado"]:
        return "Use um tom acolhedor, calmo e empático. Responda com frases simples e positivas."
    elif ultima_emocao in ["feliz", "grato", "animado"]:
        return "Use um tom leve, entusiasmado e positivo. Reforce o bom humor do usuário."
    elif ultima_emocao in ["irritado", "raivoso"]:
        return "Use um tom calmo, direto e respeitoso. Evite piadas ou ironia."
    elif ultima_emocao in ["ansioso", "confuso"]:
        return "Use um tom tranquilizador. Dê respostas claras e objetivas para reduzir a ansiedade."
    else:
        return "Use um tom neutro e gentil."

def ia_fez_uma_pergunta(mensagem_ia):
    """
    Verifica se a última mensagem da IA foi uma pergunta real para o usuário.
    """
    mensagem_ia = mensagem_ia.strip().lower()

    if mensagem_ia.endswith("?"):
        return True
    perguntas_comuns = [
        "você gostaria", "deseja continuar", "posso ajudar em mais algo",
        "quer que eu", "gostaria que eu", "quer saber mais", "quer continuar",
        "prefere parar", "deseja que eu continue", "o que você acha",
    ]
    return any(p in mensagem_ia for p in perguntas_comuns)


# <--- MODIFICADO: Função agora aceita `tom_do_usuario` para evitar uma chamada de API extra.
def responder_com_inteligencia(pergunta_usuario, modelo, historico_chat, memoria, resumo_contexto="", tom_do_usuario=None):
    """
    Decide como responder, com uma instrução de idioma reforçada e precisa.
    """
    idioma_da_pergunta = detectar_idioma_com_ia(pergunta_usuario)
    instrucao_idioma_reforcada = f"Sua regra mais importante e inegociável é responder estritamente no seguinte idioma: '{idioma_da_pergunta}'. Não use nenhum outro idioma sob nenhuma circunstância."
    entrada_curta = len(pergunta_usuario.strip()) <= 3
    resposta_memoria = None

    if entrada_curta and "ultima_pergunta_ia" in st.session_state:
        ultima = st.session_state["ultima_pergunta_ia"]
        if ia_fez_uma_pergunta(ultima):
            pergunta_usuario = f"Minha resposta é: '{pergunta_usuario}'. Com base na sua pergunta anterior: '{ultima}'"
        else:
            resposta_memoria = buscar_resposta_local(pergunta_usuario, memoria)
    else:
        resposta_memoria = buscar_resposta_local(pergunta_usuario, memoria)

    if modelo_embedding and st.session_state.get('vetores_perguntas') is not None:
        try:
            vetor_pergunta_usuario = modelo_embedding.encode([pergunta_usuario])
            scores_similaridade = cosine_similarity(
                vetor_pergunta_usuario, st.session_state.vetores_perguntas)
            indice_melhor_match = np.argmax(scores_similaridade)
            score_maximo = scores_similaridade[0, indice_melhor_match]
            LIMIAR_CONFIANCA = 0.8

            if score_maximo > LIMIAR_CONFIANCA:
                logging.info(
                    f"Resposta encontrada na memória local com confiança de {score_maximo:.2%}.")
                st.info(
                    f"Resposta encontrada na memória local (Confiança: {score_maximo:.2%}) 🧠")
                respostas_possiveis = st.session_state.base_de_conhecimento[
                    'respostas'][indice_melhor_match]
                resposta_local = random.choice(respostas_possiveis)['texto']
                return {"texto": resposta_local, "origem": "local"}
        except Exception as e:
            logging.error(f"Erro ao processar com modelo local: {e}")
            st.warning(
                f"Erro ao processar com modelo local: {e}. Usando OpenAI.")

    username = st.session_state.get("username", "default")
    preferencias = carregar_preferencias(username)
    
    # <--- MODIFICADO: Usa o tom já detectado em vez de chamar a API de novo.
    if tom_do_usuario:
        st.sidebar.info(f"Tom detectado: {tom_do_usuario}")

    if precisa_buscar_na_web(pergunta_usuario):
        logging.info(
            f"Iniciando busca na web para a pergunta: '{pergunta_usuario}'")
        st.info("Buscando informações em tempo real na web... 🌐")
        contexto_da_web = buscar_na_internet(pergunta_usuario)

        prompt_sistema = f"""{instrucao_idioma_reforcada}\n\nVocê é Jarvis, um assistente prestativo. Sua tarefa é responder à pergunta do usuário de forma clara e direta, baseando-se ESTRITAMENTE nas informações de contexto da web.\n\nINFORMAÇÕES SOBRE SEU USUÁRIO, ISRAEL: {json.dumps(preferencias, ensure_ascii=False)}\nO tom atual do usuário parece ser: {tom_do_usuario}.\n\nContexto da Web:\n{contexto_da_web}"""
    else:
        logging.info("Pergunta não requer busca na web, consultando a OpenAI.")
        st.info("🔍 Pesquisando dados...")

        prompt_sistema = f"{instrucao_idioma_reforcada}\n\nVocê é Jarvis, um assistente prestativo."

        if tom_do_usuario:
            prompt_sistema += f"\nO tom do texto dele parece ser '{tom_do_usuario}'. Adapte seu estilo de resposta a isso."
        if preferencias_emocionais := carregar_emocoes(username):
            try: # Adicionado try-except para mais robustez
                ultima_emocao = list(preferencias_emocionais.values())[-1]
                if isinstance(ultima_emocao, dict):
                    ultima_emocao = ultima_emocao.get("emocao", "neutro")
                ajuste_de_estilo = adaptar_estilo_com_base_na_emocao(str(ultima_emocao))
                prompt_sistema += f"\nO usuário parece estar se sentindo '{ultima_emocao}' recentemente. {ajuste_de_estilo}"
            except (IndexError, TypeError) as e:
                print(f"Não foi possível obter a última emoção: {e}")


                username = st.session_state.get("username", "usuário")
        if preferencias:
            prompt_sistema += f"\nLembre-se destas preferências sobre seu usuário, {username}: {json.dumps(preferencias, ensure_ascii=False)}"

        if resumo_contexto:
            prompt_sistema += f"\nLembre-se também do contexto da conversa atual: {resumo_contexto}"

    mensagens_para_api = [{"role": "system", "content": prompt_sistema}]
    mensagens_para_api.extend(historico_chat)

    modelo_selecionado = st.session_state.get('admin_model_choice', 'gpt-4o')
    resposta_modelo = chamar_openai_com_retries(
        modelo_openai=modelo,
        mensagens=mensagens_para_api,
        modelo=modelo_selecionado
    )

    if resposta_modelo is None:
        return {
            "texto": "Desculpe, não consegui obter resposta no momento. Tente novamente em instantes.",
            "origem": "erro_api"
        }

    resposta_ia = resposta_modelo.choices[0].message.content
    st.session_state["ultima_pergunta_ia"] = resposta_ia
    return {"texto": resposta_ia, "origem": "openai_web" if 'contexto_da_web' in locals() else 'openai'}


def analisar_imagem(image_file):
    try:
        st.info("Analisando a imagem com a IA...")
        image_bytes = image_file.getvalue()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        image_type = image_file.type
        messages = [{"role": "user", "content": [{"type": "text", "text": "Descreva esta imagem em detalhes. Se for um diagrama ou texto, extraia as informações de forma estruturada."}, {
            "type": "image_url", "image_url": {"url": f"data:{image_type};base64,{base64_image}"}}]}]
        resposta_modelo = modelo.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=1024)
        st.success("Análise da imagem concluída!")
        return resposta_modelo.choices[0].message.content
    except Exception as e:
        st.error(f"Ocorreu um erro ao analisar a imagem: {e}")
        return "Não foi possível analisar a imagem."

# <--- MODIFICADO: Função agora aceita `metadados` para passar o tom do usuário adiante.
def processar_entrada_usuario(prompt_usuario, metadados=None):
    chat_id = st.session_state.current_chat_id
    active_chat = st.session_state.chats[chat_id]
    active_chat = padronizar_chat(active_chat)
    st.session_state.chats[chat_id] = active_chat

    
    if metadados is None:
        metadados = {}

    df = active_chat.get("dataframe")
    if df is not None:
        resultado_analise = analisar_dados_com_ia(prompt_usuario, df)
        active_chat["messages"].append({
            "role": "assistant",
            "type": resultado_analise["type"],
            "content": resultado_analise["content"]
        })
        salvar_chats(st.session_state["username"])
        st.rerun()
        return

    historico_chat = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in active_chat["messages"]
        if msg.get("type") == "text"
    ]

    ultima_emocao = st.session_state.get("ultima_emocao_usuario")
    if ultima_emocao:
        mensagem_sistema_emocional = {
            "role": "system",
            "content": f"Você é um assistente prestativo. Sua principal diretriz é ser sempre útil e positivo. O usuário está se sentindo {ultima_emocao}. Leve isso em consideração ao formular sua resposta, oferecendo apoio e uma perspectiva adequada à emoção atual dele, sem mencionar explicitamente a emoção."
        }
        historico_chat.insert(0, mensagem_sistema_emocional)

    resumo_contexto = active_chat.get("resumo_curto_prazo", "")
    contexto_do_arquivo = active_chat.get("contexto_arquivo")

    if contexto_do_arquivo:
        tipos_de_codigo = ('.py', '.js', '.ts', '.html', '.htm', '.css', '.php', '.java', '.kt', '.c', '.cpp', '.h', '.cs', '.rb', '.go', '.swift', '.sql', '.json', '.xml', '.yaml', '.yml', '.md', '.sh', '.bat', '.ps1', '.R', '.pl', '.lua')
        nome_arquivo = active_chat.get("processed_file_name", "").lower()

        if nome_arquivo.endswith(tipos_de_codigo):
            # MODO PROGRAMAÇÃO (CORRETO)
            prompt_sistema_programacao = """
            Você é Jarvis, um programador expert e assistente de código sênior.
            Sua tarefa é analisar, refatorar, depurar e criar código com base no contexto fornecido e nas solicitações do usuário.
            Responda sempre de forma clara, fornecendo o código em blocos formatados (ex: ```python ... ```) e explicando suas sugestões.
            Seja preciso, eficiente e siga as melhores práticas de programação.
            """
            historico_para_analise = [
                {"role": "system", "content": prompt_sistema_programacao},
                {"role": "user", "content": f"O seguinte arquivo de código está em contexto para nossa conversa:\n`{nome_arquivo}`\n\nCONTEÚDO DO ARQUIVO:\n---\n{contexto_do_arquivo}\n---"},
                {"role": "assistant", "content": f"Entendido. O arquivo `{nome_arquivo}` foi carregado. Estou pronto para ajudar com o código."}
            ]
        else:
            # MODO DOCUMENTO/DADOS (CORRETO)
            historico_para_analise = [
                {"role": "system", "content": "Você é um assistente especialista em análise de dados e documentos. Responda às perguntas do usuário baseando-se ESTRITAMENTE no conteúdo do documento fornecido abaixo."},
                {"role": "user", "content": f"CONTEÚDO DO DOCUMENTO PARA ANÁLISE:\n---\n{contexto_do_arquivo}\n---"},
                {"role": "assistant", "content": "Entendido. O conteúdo do documento foi carregado. Estou pronto para responder suas perguntas sobre ele."}
            ]

        # Agora, esta linha usa o histórico que foi definido corretamente acima
        historico_para_analise.extend(historico_chat)
        historico_final = historico_para_analise
    else:
        historico_final = historico_chat



    # <--- MODIFICADO: Passa o tom do usuário (dos metadados) para a função de resposta.
    tom_do_usuario = metadados.get("sentimento_usuario")
    dict_resposta = responder_com_inteligencia(
        prompt_usuario, modelo, historico_final, memoria, resumo_contexto, tom_do_usuario=tom_do_usuario
    )

    active_chat["messages"].append({
        "role": "assistant",
        "type": "text",
        "content": dict_resposta["texto"],
        "origem": dict_resposta["origem"]
    })

    if len(active_chat["messages"]) == 2 and active_chat.get("title", "") == "Novo Chat":

        with st.spinner("Criando título para o chat..."):
            novo_titulo = gerar_titulo_conversa_com_ia(active_chat["messages"])
            active_chat["title"] = novo_titulo

    salvar_chats(st.session_state["username"])
    st.rerun()


def salvar_feedback(username, rating, comment):
    """Salva o feedback do usuário em um arquivo JSON."""
    feedback_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "username": username,
        "rating": rating,
        "comment": comment
    }

    caminho_arquivo = "dados/feedback.json"
    os.makedirs("dados", exist_ok=True)

    dados_existentes = []
    if os.path.exists(caminho_arquivo) and os.path.getsize(caminho_arquivo) > 0:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            try:
                dados_existentes = json.load(f)
            except json.JSONDecodeError:
                dados_existentes = []

    if not isinstance(dados_existentes, list):
        dados_existentes = []

    dados_existentes.append(feedback_data)

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados_existentes, f, indent=4, ensure_ascii=False)


def gerar_resumo_curto_prazo(historico_chat):
    """Gera um resumo da conversa recente usando a OpenAI."""
    print("Gerando resumo de curto prazo...")
    ultimas_mensagens = historico_chat[-10:]
    conversa_para_resumir = "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in ultimas_mensagens])

    prompt = f"""
    A seguir está um trecho de uma conversa entre 'user' e 'assistant'. 
    Sua tarefa é ler este trecho e resumi-lo em uma única e concisa frase em português que capture o tópico principal ou a última informação relevante discutida.
    Este resumo será usado como memória de curto prazo para o assistente.

    Exemplo de resumo: "O usuário estava perguntando sobre os detalhes de deploy de aplicações Streamlit."

    Conversa:
    {conversa_para_resumir}

    Resumo conciso em uma frase:
    """

    try:
        modelo_selecionado = st.session_state.get(
            'admin_model_choice', 'gpt-4o')
        resposta_modelo = modelo.chat.completions.create(
            model=modelo_selecionado,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )
        resumo = resposta_modelo.choices[0].message.content.strip()
        return resumo
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        return ""


def gerar_titulo_conversa_com_ia(mensagens):
    """Usa a IA para criar um título curto para a conversa."""
    historico_para_titulo = [
        f"{msg['role']}: {msg['content']}" for msg in mensagens if msg.get('type') == 'text']
    conversa_inicial = "\n".join(historico_para_titulo)

    prompt = f"""
    Abaixo está o início de uma conversa entre um usuário e um assistente de IA. 
    Sua tarefa é criar um título curto e conciso em português (máximo de 5 palavras) que resuma o tópico principal da conversa.
    Responda APENAS com o título, sem nenhuma outra palavra ou pontuação.

    CONVERSA:
    {conversa_inicial}

    TÍTULO CURTO:
    """

    try:
        modelo_selecionado = st.session_state.get(
            'admin_model_choice', 'gpt-4o')
        resposta_modelo = modelo.chat.completions.create(
            model=modelo_selecionado,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=15,
            temperature=0.2
        )
        titulo = resposta_modelo.choices[0].message.content.strip().replace(
            '"', '')
        return titulo if titulo else "Chat"
    except Exception as e:
        print(f"Erro ao gerar título: {e}")
        return "Chat"


def precisa_buscar_na_web(pergunta_usuario):
    """
    Usa a OpenAI para decidir rapidamente se uma pergunta requer busca na web.
    """
    if any(p in pergunta_usuario.lower() for p in ["link", "vídeo", "site", "inscrição", "cadastro", "url"]):
        return True

    print("Verificando necessidade de busca na web...")
    prompt = f"""
    Analise a pergunta do usuário e determine se ela requer informações em tempo real ou muito recentes para ser respondida com precisão.
    Responda apenas com a palavra 'BUSCA_WEB' se a busca for necessária.
    Responda apenas com a palavra 'CHAT_PADRAO' se for uma pergunta geral, criativa, sobre a memória interna ou que não dependa do tempo.

    Exemplos que precisam de busca:
    - Qual a cotação do dólar hoje?
    - Quem ganhou o jogo do Sport ontem?
    - Quais as últimas notícias sobre a OpenAI?
    - Como está o tempo em Recife?

    Exemplos que NÃO precisam de busca:
    - Quem descobriu o Brasil?
    - Me dê ideias para um prompt de imagem
    - Quem é você?
    - Crie uma lista de compras

    Pergunta do usuário: "{pergunta_usuario}"
    """
    try:
        modelo_selecionado = st.session_state.get(
            'admin_model_choice', 'gpt-4o')
        resposta_modelo = modelo.chat.completions.create(
            model=modelo_selecionado,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10
        )
        decisao = resposta_modelo.choices[0].message.content.strip().upper()
        print(f"Decisão do classificador: {decisao}")
        return "BUSCA_WEB" in decisao
    except Exception as e:
        print(f"Erro ao verificar necessidade de busca: {e}")
        return False


def buscar_na_internet(pergunta_usuario):
    """
    Pesquisa a pergunta na web usando a API Serper e retorna um resumo dos resultados com links.
    """
    print(f"Pesquisando na web por: {pergunta_usuario}")

    if not api_key_serper:
        return "ERRO: A chave da API Serper não foi configurada."

    url = "[https://google.serper.dev/search](https://google.serper.dev/search)"
    payload = json.dumps({"q": pergunta_usuario, "gl": "br", "hl": "pt-br"})
    headers = {'X-API-KEY': api_key_serper, 'Content-Type': 'application/json'}

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        resultados = response.json().get('organic', [])

        if not resultados:
            return "Nenhum resultado encontrado na web."

        contexto_web = []
        for i, item in enumerate(resultados[:3]):
            titulo = item.get('title', 'Sem título')
            snippet = item.get('snippet', 'Sem descrição')
            link = item.get('link', '#')
            contexto_web.append(
                f"🔹 **{titulo}**\n{snippet}\n🔗 [Acessar site]({link})\n")

        return "\n\n".join(contexto_web)

    except Exception as e:
        return f"ERRO ao pesquisar na web: {e}"


def executar_analise_profunda(df):
    """Executa um conjunto de análises de dados e retorna a saída como string."""
    buffer = io.StringIO()
    from contextlib import redirect_stdout
    with redirect_stdout(buffer):
        print("--- RESUMO ESTATÍSTICO (NUMÉRICO) ---\n")
        print(df.describe(include=np.number)) # Mais explícito
        print("\n\n--- RESUMO CATEGÓRICO ---\n")
        if not df.select_dtypes(include=['object', 'category']).empty:
            print(df.describe(include=['object', 'category']))
        else:
            print("Nenhuma coluna de texto (categórica) encontrada.")
        print("\n\n--- CONTAGEM DE VALORES ÚNICOS ---\n")
        print(df.nunique())
        print("\n\n--- VERIFICAÇÃO DE DADOS FALTANTES (NULOS) ---\n")
        print(df.isnull().sum())
        print("\n\n--- MATRIZ DE CORRELAÇÃO (APENAS NUMÉRICO) ---\n")
        # numeric_only=True é o padrão em versões recentes do pandas, mas é bom manter por compatibilidade.
        print(df.corr(numeric_only=True))
    return buffer.getvalue()


def analisar_dados_com_ia(prompt_usuario, df):
    """
    Usa a IA em um processo de duas etapas para analisar dados.
    """
    st.info("Gerando e executando análise...")

    schema = df.head().to_string()

    prompt_gerador_codigo = f"""
Você é um gerador de código Python para análise de dados com Pandas.
O usuário tem um dataframe `df` com o seguinte schema:
{schema}

A pergunta do usuário é: "{prompt_usuario}"

Sua tarefa é gerar um código Python, e SOMENTE o código, para obter os dados necessários para responder à pergunta.
- Use a função `print()` para exibir todos os resultados brutos necessários (tabelas, contagens, médias, etc.).
- Se a pergunta pedir explicitamente um gráfico, use `plotly.express` e atribua a figura a uma variável chamada `fig`.
- **IMPORTANTE: Ao usar funções de agregação como `.mean()`, `.sum()`, ou `.corr()`, sempre inclua o argumento `numeric_only=True` para evitar erros com colunas de texto. Exemplo: `df.mean(numeric_only=True)`.**
- Responda apenas com o bloco de código Python.
"""

    try:
        modelo_selecionado = st.session_state.get(
            'admin_model_choice', 'gpt-4o')
        resposta_modelo_codigo = modelo.chat.completions.create(
            model=modelo_selecionado,
            messages=[{"role": "user", "content": prompt_gerador_codigo}],
            temperature=0,
        )
        codigo_gerado = resposta_modelo_codigo.choices[0].message.content.strip()

        # Limpeza do código gerado
        if codigo_gerado.startswith("```python"):
            codigo_gerado = codigo_gerado[9:].strip()
        elif codigo_gerado.startswith("```"):
            codigo_gerado = codigo_gerado[3:].strip()
        if codigo_gerado.endswith("```"):
            codigo_gerado = codigo_gerado[:-3].strip()

        local_vars = {"df": df, "pd": pd, "px": px}
        output_buffer = io.StringIO()

        from contextlib import redirect_stdout
        with redirect_stdout(output_buffer):
            exec(codigo_gerado, local_vars)

        if "fig" in local_vars:
            st.success("Gráfico gerado com sucesso!")
            return {"type": "plot", "content": local_vars["fig"]}

        resultados_brutos = output_buffer.getvalue().strip()

        if not resultados_brutos:
            return {"type": "text", "content": "A análise foi executada, mas não produziu resultados visíveis."}

        st.info("Análise executada. Interpretando resultados para o usuário...")

        prompt_interpretador = f"""
        Você é Jarvis, um assistente de IA especialista em análise de dados. Sua tarefa é atuar como um analista de negócios e explicar os resultados de uma análise de forma clara, visual e com insights para um usuário final.
        A pergunta original do usuário foi: "{prompt_usuario}"
        Abaixo estão os resultados brutos obtidos de um script Python:
        --- DADOS BRUTOS ---
        {resultados_brutos}
        --- FIM DOS DADOS BRUTOS ---

        Por favor, transforme esses dados brutos em um relatório amigável.
        - **NUNCA** mostre as tabelas de dados brutos ou o texto técnico.
        - Use Markdown, emojis (como 📊, 👤, 🚨) e negrito para criar um "Dashboard de Insights Rápidos".
        - Apresente os números de forma clara (ex: "56,8%" em vez de "0.56788").
        - Identifique o principal "Insight Estratégico" ou "Alerta" que os dados revelam.
        - No final, sugira 2 ou 3 perguntas inteligentes que o usuário poderia fazer para aprofundar a análise.
        """

        modelo_selecionado = st.session_state.get(
            'admin_model_choice', 'gpt-4o')
        resposta_modelo_interpretacao = modelo.chat.completions.create(
            model=modelo_selecionado,
            messages=[{"role": "user", "content": prompt_interpretador}],
            temperature=0.4,
        )

        resumo_claro = resposta_modelo_interpretacao.choices[0].message.content
        st.success("Relatório gerado!")
        return {"type": "text", "content": resumo_claro}

    except Exception as e:
        error_message = f"Desculpe, ocorreu um erro ao tentar analisar sua pergunta:\n\n**Erro:**\n`{e}`\n\n**Código que falhou:**\n```python\n{codigo_gerado if 'codigo_gerado' in locals() else 'N/A'}\n```"
        return {"type": "text", "content": error_message}


# --- INTERFACE GRÁFICA (STREAMLIT) ---
st.set_page_config(page_title="Jarvis IA", layout="wide")
st.markdown("""<style>.stApp { background-color: #0d1117; color: #c9d1d9; } .stTextInput, .stChatInput textarea { background-color: #161b22; color: #c9d1d9; border-radius: 8px; } .stButton button { background-color: #151b22; color: white; border-radius: 10px; border: none; }</style>""", unsafe_allow_html=True)

memoria = carregar_memoria()

# --- GESTÃO DE CHATS ---
def padronizar_chat(chat):
    return {
        "title": chat.get("title", "Novo Chat"),
        "messages": chat.get("messages", []),
        "contexto_arquivo": chat.get("contexto_arquivo"),
        "processed_file_name": chat.get("processed_file_name"),
        "dataframe": chat.get("dataframe"),
        "resumo_curto_prazo": chat.get("resumo_curto_prazo", ""),
        "ultima_mensagem_falada": chat.get("ultima_mensagem_falada")
    }


def create_new_chat():
    chat_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    st.session_state.chats[chat_id] = {
        "title": "Novo Chat",
        "messages": [],
        "contexto_arquivo": None,
        "processed_file_name": None,
        "dataframe": None,
        "resumo_curto_prazo": "",
        "ultima_mensagem_falada": None
    }
    st.session_state.current_chat_id = chat_id

    # st.rerun() não é necessário aqui, pois o on_click do botão já fará isso.

def switch_chat(chat_id):
    st.session_state.current_chat_id = chat_id


def delete_chat(chat_id_to_delete):
    if chat_id_to_delete in st.session_state.chats:
        del st.session_state.chats[chat_id_to_delete]

        if st.session_state.current_chat_id == chat_id_to_delete:
            if st.session_state.chats:
                st.session_state.current_chat_id = list(
                    st.session_state.chats.keys())[-1]
            else:
                create_new_chat()

        salvar_chats(st.session_state["username"])
        # st.rerun() não é necessário, o on_click do botão fará isso.

# <--- NOVO: Função para o botão de logout
def fazer_logout():
    """Limpa a sessão para deslogar o usuário."""
    st.session_state.clear()


# --- INICIALIZAÇÃO E SIDEBAR ---
if "chats" not in st.session_state:
    raw_chats = carregar_chats(st.session_state["username"])
    st.session_state.chats = {
        chat_id: padronizar_chat(chat_data)
        for chat_id, chat_data in raw_chats.items()
    }

if not st.session_state.chats:
    create_new_chat()

if "current_chat_id" not in st.session_state or st.session_state.current_chat_id not in st.session_state.chats:
    st.session_state.current_chat_id = list(st.session_state.chats.keys())[-1]

chat_id = st.session_state.current_chat_id
active_chat = padronizar_chat(st.session_state.chats[chat_id])
st.session_state.chats[chat_id] = active_chat



def img_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


gif_b64 = img_to_base64("assets/jarvis-gif.gif")

with st.sidebar:
    st.markdown(
        f"""
        <div style="text-align: center;">
            <img src="data:image/gif;base64,{gif_b64}" width="150" style="display: inline-block;" />
            <h1 style="font-size: 28px; font-weight: bold; color: #00f0ff; margin-top: 10px;">
                🤖 Jarvis IA
            </h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.divider()
    st.sidebar.header("Painel do Usuário")
    st.sidebar.page_link("pages/3_Gerenciar_Preferencias.py",
                         label="Minhas Preferências", icon="⚙️")
    st.sidebar.page_link("pages/7_emocoes.py",
                         label="Gerenciar Emoções", icon="🧠")
    st.sidebar.page_link("pages/4_Suporte_e_Ajuda.py",
                         label="Suporte e Ajuda", icon="💡")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📚 Ferramentas Externas")

    st.sidebar.markdown("""
    <style>
    a.link-button { display: block; background-color: #1f77b4; color: white !important; padding: 10px; text-align: center; border-radius: 8px; text-decoration: none; margin: 5px 0; font-weight: bold; transition: 0.3s; }
    a.link-button:hover { background-color: #005fa3; }
    </style>
    <a class='link-button' href='https://jarvis-lembrete.streamlit.app/' target='_blank'>🔔 Jarvis Lembrete</a>
    <a class='link-button' href='https://jarvis-ia-video-analysis.streamlit.app/' target='_blank'>🎥 Analisador de Mídia</a>
    """, unsafe_allow_html=True)

    if st.session_state.get("username") == ADMIN_USERNAME:
        st.sidebar.divider()
        st.sidebar.header("Painel do Admin")
        st.sidebar.page_link("pages/1_Gerenciar_Memoria.py",
                             label="Gerenciar Memória", icon="🧠")
        st.sidebar.page_link("pages/2_Status_do_Sistema.py",
                             label="Status do Sistema", icon="📊")
        st.sidebar.page_link("pages/5_Gerenciamento_de_Assinaturas.py",
                             label="Gerenciar Assinaturas", icon="🔑")
        st.sidebar.page_link("pages/6_Visualizar_Feedback.py",
                             label="Visualizar Feedback", icon="📊")
        st.sidebar.radio(
            "Alternar Modelo OpenAI (Sessão Atual):",
            options=['gpt-4o', 'gpt-3.5-turbo'],
            key='admin_model_choice',
            help="Esta opção afeta apenas a sua sessão de administrador e reseta ao sair. O padrão para todos os outros usuários é sempre gpt-4o."
        )

    st.sidebar.divider()

    # <--- MODIFICADO: Uso de on_click para estabilidade
    st.button("➕ Novo Chat", use_container_width=True, type="primary", on_click=create_new_chat)

    voz_ativada = st.checkbox(
        "🔊 Ouvir respostas do Jarvis", value=False, key="voz_ativada")
    st.divider()

    st.write("#### Configurações de Voz")
    idioma_selecionado = st.selectbox(
        "Idioma da Fala (Saída)",
        options=['pt-BR', 'en-US', 'es-ES', 'fr-FR', 'de-DE', 'it-IT'],
        index=0,
        key="idioma_fala",
        help="Escolha o idioma para o Jarvis falar suas respostas."
    )

with st.sidebar:
    st.write("#### Histórico de Chats")

    if "chats" in st.session_state:
        # Itera sobre uma cópia para evitar problemas ao deletar
        for id, chat_data in reversed(list(st.session_state.chats.items())):
            chat_selected = (id == st.session_state.current_chat_id)
            col1, col2, col3 = st.columns([0.6, 0.2, 0.2])

            with col1:
                # CORREÇÃO 1 (Já feita por você): Botão de exibição
                st.button(chat_data.get("title", "Chat sem título"), key=f"chat_{id}",
                             use_container_width=True,
                             type="primary" if chat_selected else "secondary",
                             on_click=switch_chat,
                             args=(id,))
            with col2:
                with st.popover("✏️", use_container_width=True):
                    # CORREÇÃO 2: Campo de texto para renomear
                    new_title = st.text_input(
                        "Novo título:", value=chat_data.get("title", ""), key=f"rename_input_{id}")
                    if st.button("Salvar", key=f"save_rename_{id}"):
                        st.session_state.chats[id]["title"] = new_title
                        salvar_chats(st.session_state["username"])
                        st.rerun() 
            with col3:
                with st.popover("🗑️", use_container_width=True):
                    # CORREÇÃO 3: Mensagem de confirmação de exclusão
                    st.write(
                        f"Tem certeza que deseja excluir **{chat_data.get('title', 'este chat')}**?")
                    
                    st.button("Sim, excluir!", type="primary", key=f"delete_confirm_{id}",
                                  on_click=delete_chat,
                                  args=(id,))

        st.button("🚪 Sair", use_container_width=True, type="secondary", on_click=fazer_logout)
    st.divider()

if st.session_state.get("show_feedback_form", False) and st.session_state.get("username") != ADMIN_USERNAME:
    with st.expander("⭐ Deixe seu Feedback", expanded=False):
        st.write("Sua opinião é importante para a evolução do Jarvis!")

        with st.form("sidebar_feedback_form", clear_on_submit=True):
            rating = st.slider("Sua nota:", 1, 5, 3, key="feedback_rating")
            comment = st.text_area(
                "Comentários (opcional):", key="feedback_comment")

            submitted = st.form_submit_button(
                "Enviar Feedback", use_container_width=True, type="primary")
            if submitted:
                salvar_feedback(st.session_state["username"], rating, comment)
                st.toast("Obrigado pelo seu feedback!", icon="💖")
                st.session_state["show_feedback_form"] = False
                st.rerun()

with st.expander("📂 Anexar Arquivos"):
    tipos_dados = ["csv", "xlsx", "xls", "json"]
    tipos_documentos = [
        "pdf", "docx", "txt", "py", "js", "ts", "html", "htm", "css",
        "php", "java", "kt", "c", "cpp", "h", "cs", "rb", "go",
        "swift", "sql", "xml", "yaml", "yml", "md", "sh", "bat", "ps1", "R", "pl", "lua"
    ]

    chat_id_for_key = st.session_state.current_chat_id

    arquivo = st.file_uploader(
        "📄 Documento, Código ou Dados (.csv, .xlsx, .json)",
        type=tipos_dados + tipos_documentos,
        key=f"uploader_doc_{chat_id_for_key}"
    )

    if arquivo and arquivo.name != active_chat.get("processed_file_name"):
        active_chat["contexto_arquivo"] = None
        active_chat["dataframe"] = None
        file_extension = arquivo.name.split('.')[-1].lower()

        if file_extension in tipos_dados:
            with st.spinner(f"Analisando '{arquivo.name}'..."):
                try:
                    df = None
                    if file_extension == 'csv':
                        df = pd.read_csv(arquivo)
                    elif file_extension in ['xlsx', 'xls']:
                        df = pd.read_excel(arquivo, engine='openpyxl')
                    elif file_extension == 'json':
                        df = pd.read_json(arquivo)

                    if df is not None:
                        active_chat["dataframe"] = df
                        active_chat["processed_file_name"] = arquivo.name
                        st.success(
                            f"Arquivo '{arquivo.name}' carregado! Jarvis está em modo de análise.")
                        active_chat["messages"].append({
                            "role": "assistant", "type": "text",
                            "content": f"Arquivo `{arquivo.name}` carregado. Agora sou sua assistente de análise de dados. Peça-me para gerar resumos, médias, ou criar gráficos."
                        })
                except Exception as e:
                    st.error(f"Erro ao carregar o arquivo de dados: {e}")
        else:
            active_chat["contexto_arquivo"] = extrair_texto_documento(arquivo)
            active_chat["processed_file_name"] = arquivo.name

        salvar_chats(st.session_state["username"])
        st.rerun()

    imagem = st.file_uploader(
        "🖼️ Imagem", type=["png", "jpg", "jpeg"], key=f"uploader_img_{chat_id_for_key}")
    if imagem and imagem.name != active_chat.get("processed_file_name"):
        st.image(imagem, width=200)
        active_chat["contexto_arquivo"] = analisar_imagem(imagem)
        active_chat["processed_file_name"] = imagem.name
        salvar_chats(st.session_state["username"])
        st.rerun()

    if active_chat.get("dataframe") is not None:
        st.info("Jarvis em 'Modo de Análise de Dados'.")
        with st.expander("Ver resumo dos dados"):
            st.dataframe(active_chat["dataframe"].head())
            buffer = io.StringIO()
            active_chat["dataframe"].info(buf=buffer)
            st.text(buffer.getvalue())
        # <--- MODIFICADO: Uso de on_click para estabilidade
        st.button("🗑️ Sair do Modo de Análise", type="primary", key=f"forget_btn_data_{chat_id}", on_click=create_new_chat)

    elif active_chat.get("contexto_arquivo"):
        st.info("Jarvis está em 'Modo de Análise de Documento'.")
        st.text_area("Conteúdo extraído:",
                     value=active_chat["contexto_arquivo"], height=200, key=f"contexto_arquivo_{chat_id}")
        # <--- MODIFICADO: Uso de on_click para estabilidade
        st.button("🗑️ Esquecer Arquivo Atual", type="primary", key=f"forget_btn_doc_{chat_id}", on_click=create_new_chat)


# --- ÁREA PRINCIPAL DO CHAT ---
st.write(f"### {active_chat.get('title', 'Chat sem título')}")


for i, mensagem in enumerate(active_chat["messages"]):
    with st.chat_message(mensagem["role"]):
        if mensagem.get("type") == "plot":
            st.plotly_chart(mensagem["content"], use_container_width=True)
        elif mensagem.get("type") == "image":
            st.image(mensagem["content"], caption=mensagem.get("prompt", "Imagem gerada"))
            try:
                base64_data = mensagem["content"].split(",")[1]
                image_bytes = base64.b64decode(base64_data)
                st.download_button(
                    label="📥 Baixar Imagem",
                    data=image_bytes,
                    file_name="imagem_gerada_jarvis.png",
                    mime="image/png",
                    key=f"download_img_{i}"  
                )
            except Exception as e:
                st.warning(f"Não foi possível gerar o botão de download: {e}")
        else:
            st.write(mensagem["content"])

        if mensagem.get("origem") == "openai" and st.session_state.get("username") == ADMIN_USERNAME:
            if i > 0:
                pergunta_original = active_chat["messages"][i-1]["content"]
                resposta_original = mensagem["content"]
                cols = st.columns([1, 1, 10])

                with cols[0]:
                    if st.button("✅", key=f"save_{i}", help="Salvar resposta na memória"):
                        adicionar_a_memoria(
                            pergunta_original, resposta_original, modelo_embedding)
                        mensagem["origem"] = "openai_curado"
                        salvar_chats(st.session_state["username"])
                        st.rerun()
                with cols[1]:
                    with st.popover("✏️", help="Editar antes de salvar"):
                        with st.form(key=f"edit_form_{i}"):
                            st.write(
                                "Ajuste a pergunta e/ou a resposta antes de salvar.")
                            pergunta_editada = st.text_area(
                                "Pergunta:", value=pergunta_original, height=100)
                            resposta_editada = st.text_area(
                                "Resposta:", value=resposta_original, height=200)
                            if st.form_submit_button("Salvar Edição"):
                                adicionar_a_memoria(
                                    pergunta_editada, resposta_editada, modelo_embedding)
                                mensagem["origem"] = "openai_curado"
                                salvar_chats(st.session_state["username"])
                                st.rerun()

st.markdown("""
    <script>
        const chatContainer = window.parent.document.querySelector('.element-container:has(.stChatMessage)');
        if (chatContainer) { setTimeout(() => { chatContainer.scrollTop = chatContainer.scrollHeight; }, 100); }
    </script>
""", unsafe_allow_html=True)

if active_chat["messages"] and active_chat["messages"][-1]["role"] == "assistant" and voz_ativada:
    if active_chat["messages"][-1].get("type") == "text":
        resposta_ia = active_chat["messages"][-1]["content"]
        if resposta_ia != active_chat.get("ultima_mensagem_falada"):
            idioma_detectado = detectar_idioma_com_ia(resposta_ia)
            texto_limpo_para_fala = preparar_texto_para_fala(resposta_ia)
            resposta_formatada_para_voz = json.dumps(texto_limpo_para_fala)
            st.components.v1.html(f"""
            <script>
                function getVoices() {{ return new Promise(resolve => {{ let voices = speechSynthesis.getVoices(); if (voices.length) {{ resolve(voices); return; }} speechSynthesis.onvoiceschanged = () => {{ voices = speechSynthesis.getVoices(); resolve(voices); }}; }}); }}
                async function speak() {{ const text = {resposta_formatada_para_voz}; const idioma = '{idioma_detectado}'; if (!text || text.trim() === '') return; const allVoices = await getVoices(); let voicesForLang = allVoices.filter(v => v.lang.startsWith(idioma)); let desiredVoice; if (voicesForLang.length > 0) {{ if (idioma === 'pt') {{ const ptFemaleNames = ['Microsoft Francisca Online (Natural) - Portuguese (Brazil)', 'Microsoft Maria - Portuguese (Brazil)', 'Google português do Brasil', 'Luciana', 'Joana']; for (const name of ptFemaleNames) {{ desiredVoice = voicesForLang.find(v => v.name === name); if (desiredVoice) break; }} }} if (!desiredVoice) {{ const femaleMarkers = ['Female', 'Feminino', 'Femme', 'Mujer']; desiredVoice = voicesForLang.find(v => femaleMarkers.some(marker => v.name.includes(marker))); }} if (!desiredVoice) {{ desiredVoice = voicesForLang.find(v => v.default); }} if (!desiredVoice) {{ desiredVoice = voicesForLang.find(v => !v.localService); }} if (!desiredVoice) {{ desiredVoice = voicesForLang[0]; }} }} const utterance = new SpeechSynthesisUtterance(text); if (desiredVoice) {{ utterance.voice = desiredVoice; utterance.lang = desiredVoice.lang; }} else {{ utterance.lang = idioma; }} utterance.pitch = 1.0; utterance.rate = 1.0; speechSynthesis.cancel(); speechSynthesis.speak(utterance); }}
                speak();
            </script>
            """, height=0)
            active_chat["ultima_mensagem_falada"] = resposta_ia
            salvar_chats(st.session_state["username"])


if 'pdf_para_download' in st.session_state:
    with st.chat_message("assistant"):
        st.download_button(
            label="📥 Baixar PDF",
            data=st.session_state['pdf_para_download'],
            file_name=st.session_state['pdf_filename'],
            mime="application/pdf",
            on_click=limpar_pdf_da_memoria
        )

# <--- NOVO: Função para lidar com comandos, limpando o bloco principal
def processar_comandos(prompt_usuario, active_chat):
    """Processa comandos especiais como /imagine, /pdf, etc. Retorna True se um comando foi processado."""
    prompt_lower = prompt_usuario.lower().strip()

    if prompt_lower.startswith("/lembrese "):
        texto_para_lembrar = prompt_usuario[10:].strip()
        if texto_para_lembrar:
            with st.chat_message("assistant"):
                st.info("Memorizando sua preferência...")
                processar_comando_lembrese(texto_para_lembrar)
        return True

    elif prompt_lower.startswith("/imagine "):
        prompt_da_imagem = prompt_usuario[9:].strip()
        if prompt_da_imagem:
            with st.chat_message("assistant"):
                dados_da_imagem = gerar_imagem_com_dalle(prompt_da_imagem)
                if dados_da_imagem:
                    active_chat["messages"].append(
                        {"role": "assistant", "type": "image", "content": dados_da_imagem, "prompt": prompt_da_imagem}
                    )
                    salvar_chats(st.session_state["username"])
            st.rerun()
        return True

    elif prompt_lower.startswith("/pdf "):
        topico_pdf = prompt_usuario[5:].strip()
        if topico_pdf:
            with st.chat_message("assistant"):
                with st.spinner("Criando seu PDF..."):
                    texto_completo_ia = gerar_conteudo_para_pdf(topico_pdf)
                    linhas_ia = texto_completo_ia.strip().split('\n')
                    titulo_documento = linhas_ia[0].replace('**', '').replace('###', '').replace('##', '').replace('#', '').strip()
                    texto_corpo = '\n'.join(linhas_ia[1:]).strip()
                    pdf_bytes = criar_pdf(texto_corpo, titulo_documento)
                    st.session_state['pdf_para_download'] = pdf_bytes
                    st.session_state['pdf_filename'] = f"{titulo_documento.replace(' ', '_')[:30]}.pdf"
            active_chat["messages"].append(
                {"role": "assistant", "type": "text", "content": f"Criei um PDF sobre '{titulo_documento}'. O botão de download foi exibido."})
            salvar_chats(st.session_state["username"])
            st.rerun()
        return True
    
    elif prompt_lower.startswith("/gerar_codigo "):
        descricao_codigo = prompt_usuario[14:].strip()
        if descricao_codigo:
            with st.chat_message("assistant"):
                with st.spinner(f"Gerando código para: '{descricao_codigo}'..."):
                    prompt_para_ia = f"""
                    Gere um script Python completo e funcional com base na seguinte descrição.
                    O código deve ser bem comentado, seguir as melhores práticas (PEP 8) e estar contido em um único bloco de código.
                    Descrição: "{descricao_codigo}"

                    Responda APENAS com o bloco de código Python formatado em markdown.
                    Exemplo de Resposta:
                    ```python
                    # seu código aqui
                    ```
                    """
                    modelo_selecionado = st.session_state.get('admin_model_choice', 'gpt-4o')
                    resposta_modelo = modelo.chat.completions.create(
                        model=modelo_selecionado,
                        messages=[{"role": "user", "content": prompt_para_ia}],
                        temperature=0.1,
                    )
                    codigo_gerado = resposta_modelo.choices[0].message.content
                    active_chat["messages"].append({"role": "assistant", "type": "text", "content": codigo_gerado})
                    salvar_chats(st.session_state["username"])
            st.rerun()
        return True

    elif prompt_lower.startswith(("/explicar", "/refatorar", "/depurar")):
        if not active_chat.get("contexto_arquivo"):
            st.warning("Para usar este comando, por favor, carregue um arquivo de código primeiro.")
            active_chat["messages"].append({"role": "assistant", "type": "text", "content": "Para usar este comando, por favor, carregue um arquivo de código primeiro."})
            # Opcional: Adicionar st.rerun() aqui para o aviso aparecer imediatamente
            # st.rerun() 
            return True 

        comando = prompt_lower.split(' ')[0] # /explicar, /refatorar, etc.
        instrucao_adicional = prompt_usuario[len(comando):].strip()
        nome_arquivo = active_chat.get("processed_file_name", "o arquivo atual")

        with st.chat_message("assistant"):
            with st.spinner(f"Processando '{comando}' no arquivo `{nome_arquivo}`..."):
                prompt_para_ia = f"""
                Você é um programador expert. Sua tarefa é executar a ação '{comando}' no código-fonte fornecido.

                Arquivo em análise: `{nome_arquivo}`
                Instruções adicionais do usuário: "{instrucao_adicional if instrucao_adicional else 'Nenhuma'}"

                Responda de forma clara, com explicações detalhadas e, se aplicável, forneça o bloco de código modificado ou sugerido.

                CÓDIGO-FONTE PARA ANÁLISE:
                ---
                {active_chat.get("contexto_arquivo")}
                ---
                """
                modelo_selecionado = st.session_state.get('admin_model_choice', 'gpt-4o')
                resposta_modelo = modelo.chat.completions.create(
                    model=modelo_selecionado,
                    messages=[{"role": "user", "content": prompt_para_ia}],
                    temperature=0.2,
                )
                resposta_analise = resposta_modelo.choices[0].message.content
                active_chat["messages"].append({"role": "assistant", "type": "text", "content": resposta_analise})
                salvar_chats(st.session_state["username"])
        st.rerun()
        return True

    
    elif prompt_lower == "/raiox":
        if active_chat.get("dataframe") is not None:
            df = active_chat.get("dataframe")
            with st.spinner("Executando Raio-X completo dos dados..."):
                resultados_brutos = executar_analise_profunda(df)
                prompt_interpretador = f"""Você é Jarvis, um analista de dados sênior. O usuário pediu um Raio-X completo do dataset. Abaixo estão os resultados brutos. Sua tarefa é criar um relatório claro e com insights, explicando cada seção (resumo estatístico, categorias, valores únicos, dados faltantes e correlações) para o usuário.\n\n--- DADOS BRUTOS ---\n{resultados_brutos}\n--- FIM DOS DADOS BRUTOS ---"""
                modelo_selecionado = st.session_state.get('admin_model_choice', 'gpt-4o')
                resposta_interpretada = modelo.chat.completions.create(
                    model=modelo_selecionado,
                    messages=[{"role": "user", "content": prompt_interpretador}]
                ).choices[0].message.content
                active_chat["messages"].append(
                    {"role": "assistant", "type": "text", "content": resposta_interpretada})
                salvar_chats(st.session_state["username"])
                st.rerun()
        else:
            st.warning("Para usar o comando /raiox, por favor, carregue um arquivo de dados primeiro.")
        return True
    
    return False


# --- ENTRADA DE TEXTO DO USUÁRIO (BLOCO REATORADO) ---
if prompt_usuario := st.chat_input("Fale com a Jarvis ou use /lembrese, /imagine, /pdf, /raiox, /gerar_codigo, /explicar, /refatorar, /depurar..."):
    # Adiciona a mensagem do usuário ao histórico imediatamente
    active_chat["messages"].append(
        {"role": "user", "type": "text", "content": prompt_usuario})
    salvar_chats(st.session_state["username"])

    # Tenta processar como um comando especial
    comando_foi_processado = processar_comandos(prompt_usuario, active_chat)

    # Se NÃO for um comando, processa como um chat normal
    if not comando_foi_processado:
        # 1. Analisa os metadados do prompt com UMA chamada de API otimizada
        metadados = analisar_metadados_prompt(prompt_usuario)
        
        # 2. Salva as emoções e outros metadados coletados
        if st.session_state.username:
            timestamp_atual = datetime.now().isoformat()
            data_hora_obj = datetime.now()
            
            emocoes_dict[timestamp_atual] = {
                "emocao": metadados.get("emocao", "neutro"),
                "sentimento_mensagem_usuario": metadados.get("sentimento_usuario", "n/a"),
                "tipo_interacao": metadados.get("tipo_interacao", "conversa_geral"),
                "topico_interacao": metadados.get("categoria", "geral"),
                "dia_da_semana": data_hora_obj.strftime('%A').lower(),
                "periodo_do_dia": "manhã" if 5 <= data_hora_obj.hour < 12 else "tarde" if 12 <= data_hora_obj.hour < 18 else "noite",
                "prompt_original": prompt_usuario
            }
            salvar_emocoes(emocoes_dict, st.session_state.username)
            # Atualiza a última emoção na sessão para uso imediato
            st.session_state["ultima_emocao_usuario"] = metadados.get("emocao", "neutro")

        # 3. Chama a função de processamento de chat, passando os metadados já coletados
        processar_entrada_usuario(prompt_usuario, metadados=metadados)