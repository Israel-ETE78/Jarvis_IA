# ==============================================================================
# === 1. IMPORTAÇÕES DE BIBLIOTECAS
# ==============================================================================
import logging
import streamlit as st
from openai import OpenAI
import json
from difflib import SequenceMatcher
import fitz  # PyMuPDF
import docx
import speech_recognition as sr
from dotenv import load_dotenv
import os
import datetime
from langdetect import detect, LangDetectException
import random
import re
import base64
import pandas as pd
from fpdf import FPDF
from auth import check_password # Sua autenticação local
from utils import carregar_preferencias, salvar_preferencias
import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import requests
import librosa
import io
import soundfile
from fpdf.enums import XPos, YPos
# ==============================================================================
# === 2. VERIFICAÇÃO DE LOGIN E CONFIGURAÇÃO INICIAL
ADMIN_USERNAME = st.secrets.get("ADMIN_USERNAME", os.getenv("ADMIN_USERNAME"))
if not ADMIN_USERNAME:
    st.error("Nome de usuário admin não encontrado! Defina ADMIN_USERNAME em .env ou secrets.")
    st.stop()
# ==============================================================================

# Executa a verificação de login primeiro
if not check_password():
    st.stop()  # Interrompe a execução do script se o login falhar


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
    api_key_serper = st.secrets.get("SERPER_API_KEY") # Usamos .get() para não dar erro se não existir
else:
    # Ambiente Local
    st.sidebar.info("Jarvis Online", icon="☁️")
    api_key = os.getenv("OPENAI_API_KEY")
    api_key_serper = os.getenv("SERPER_API_KEY")

# Validação para garantir que a chave de API foi carregada
if not api_key:
    st.error("Chave de API da OpenAI não encontrada! Verifique seu arquivo .env ou os Secrets na nuvem.")
    st.stop()

# Inicializa o modelo da OpenAI com a chave correta
modelo = OpenAI(api_key=api_key)


# ==============================================================================
# === 4. CONFIGURAÇÃO DE LOGS
# ==============================================================================

def setup_logging():
    """Configura o sistema de log para registrar eventos em um arquivo."""
    logging.basicConfig(
        filename='jarvis_log.txt',
        filemode='a', # 'a' para adicionar ao arquivo, 'w' para sobrescrever
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        encoding='utf-8'
    )

# Chame a função uma vez no início do script para configurar
setup_logging()


# ==============================================================================
# === 5. DEFINIÇÃO DAS FUNÇÕES DO APLICATIVO
# ==============================================================================
# O resto do seu código (a partir de @st.cache_resource) começa aqui...
# Chame a função uma vez no início do script para configurar
setup_logging()

# --- CARREGAR O MODELO E FERRAMENTAS ---


@st.cache_resource
def carregar_modelos_locais():
    """
    Carrega os modelos locais apenas uma vez e guarda em cache.
    """
    print("Executando CARGA PESADA do cérebro local (isso só deve aparecer uma vez)...")
    try:
        modelo_emb = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2')
        vetores_p = np.load('vetores_perguntas_v2.npy')
        base_conhecimento = joblib.load('dados_conhecimento_v2.joblib')
        return modelo_emb, vetores_p, base_conhecimento
    except Exception as e:
        # Se der erro, retorna None para tudo
        return None, None, None


# --- CARREGAR O MODELO E FERRAMENTAS ---
modelo_embedding, vetores_perguntas, base_de_conhecimento = carregar_modelos_locais()

# Exibe a mensagem de status no painel lateral
if modelo_embedding:
    st.sidebar.success("Memória ativada.", icon="💾")
else:
    st.sidebar.error("Arquivos do modelo local não encontrados.")

# --- Funções do Aplicativo ---

def limpar_pdf_da_memoria():
    """Remove os dados do PDF do st.session_state para o botão de download desaparecer."""
    if 'pdf_para_download' in st.session_state:
        del st.session_state['pdf_para_download']
    if 'pdf_filename' in st.session_state:
        del st.session_state['pdf_filename']

def gerar_conteudo_para_pdf(topico):
    """Usa a IA para gerar um texto bem formatado sobre um tópico para o PDF."""
    prompt = f"Por favor, escreva um texto detalhado e bem estruturado sobre o seguinte tópico para ser incluído em um documento PDF. Organize com parágrafos claros e, se apropriado, use listas. Tópico: '{topico}'"
    resposta_modelo = modelo.chat.completions.create(
        model="gpt-4o",
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
    except FileNotFoundError:
        print("AVISO: Arquivos de fonte não encontrados. Verifique a pasta 'assets'. Usando Helvetica.")
        FONT_FAMILY = 'Helvetica'

    # O resto da função continua exatamente igual...
    pdf.set_font(FONT_FAMILY, 'B', 18)
    pdf.multi_cell(0, 10, titulo_documento, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(15)

    texto_corpo_ajustado = texto_corpo.strip().replace('*\n', '* ').replace('-\n', '- ')
    linhas = texto_corpo_ajustado.split('\n')

    for linha in linhas:
        linha = linha.strip()
        if linha.startswith('### '):
            pdf.set_font(FONT_FAMILY, 'B', 14)
            pdf.multi_cell(0, 8, linha.lstrip('### ').strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(4)
        elif linha.startswith('## '):
            pdf.set_font(FONT_FAMILY, 'B', 16)
            pdf.multi_cell(0, 10, linha.lstrip('## ').strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(6)
        elif linha.startswith('# '):
            pdf.set_font(FONT_FAMILY, 'B', 18)
            pdf.multi_cell(0, 12, linha.lstrip('# ').strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(8)
        elif linha.startswith('**') and linha.endswith('**'):
            pdf.set_font(FONT_FAMILY, 'B', 12)
            texto_negrito = linha.strip('**')
            pdf.multi_cell(0, 7, texto_negrito, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
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
        '.py',      # Python
        '.js',      # JavaScript
        '.ts',      # TypeScript
        '.html',    # HTML
        '.htm',     # HTML
        '.css',     # CSS
        '.php',     # PHP
        '.java',    # Java
        '.kt',      # Kotlin
        '.c',       # C
        '.cpp',     # C++
        '.h',       # C/C++ Header
        '.cs',      # C#
        '.rb',      # Ruby
        '.go',      # Go
        '.swift',   # Swift
        '.sql',     # SQL (for MySQL, PostgreSQL, etc.)
        '.json',    # JSON
        '.xml',     # XML
        '.yaml',    # YAML
        '.yml',     # YAML
        '.md',      # Markdown
        '.sh',      # Shell Script
        '.bat',     # Batch Script
        '.ps1',     # PowerShell Script
        '.R',       # R
        '.pl',      # Perl
        '.lua'      # Lua
        # Adicione mais extensões conforme necessário
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
    try:
        st.info(
            f"🎨 Gerando imagem com DALL-E 3 para: '{prompt_para_imagem}'...")
        response = modelo.images.generate(
            model="dall-e-3", prompt=prompt_para_imagem, size="1024x1024", quality="standard", n=1)
        image_url = response.data[0].url
        st.success("Imagem gerada com sucesso!")
        return image_url
    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar a imagem: {e}")
        return None


def classificar_categoria(pergunta):
    prompt = f"Classifique esta pergunta em uma única categoria simples (como geografia, história, sentimentos, programação, etc):\nPergunta: {pergunta}"
    resposta = modelo.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return resposta.choices[0].message.content.strip().lower()


def detectar_tom_emocional(resposta):
    prompt = f"Qual o tom emocional desta resposta? Use uma só palavra: neutro, feliz, triste, sensível, etc.\nResposta: {resposta}"
    resposta_api = modelo.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return resposta_api.choices[0].message.content.strip().lower()

def detectar_tom_usuario(pergunta_usuario):
    """Detecta o tom emocional da pergunta do usuário."""
    prompt = f"""
    Analise o texto do usuário abaixo e resuma o tom emocional ou o estado de espírito dele em poucas palavras (ex: 'apressado', 'curioso', 'frustrado', 'descontraído', 'formal').
    Responda apenas com a descrição do tom.

    Texto do usuário: "{pergunta_usuario}"
    """
    try:
        resposta_modelo = modelo.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=20
        )
        return resposta_modelo.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro ao detectar tom do usuário: {e}")
        return "" # Retorna vazio em caso de erro


def detectar_idioma(texto):
    try:
        return detect(texto)
    except LangDetectException:
        return 'pt'


def preparar_texto_para_fala(texto):
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

def extrair_features(data, sample_rate):
    """
    Extrai 110 features de dados de áudio para ser compatível com o modelo treinado.
    """
    # MFCC (40) -> 40 mean + 40 std = 80 features
    mfcc = librosa.feature.mfcc(y=data, sr=sample_rate, n_mfcc=40)
    # Chroma (12) -> 12 mean + 12 std = 24 features
    chroma = librosa.feature.chroma_stft(y=data, sr=sample_rate)
    # ZCR -> 1 mean + 1 std = 2 features
    zcr = librosa.feature.zero_crossing_rate(data)
    # RMS -> 1 mean + 1 std = 2 features
    rms = librosa.feature.rms(y=data)
    # Spectral Centroid -> 1 mean + 1 std = 2 features
    centroid = librosa.feature.spectral_centroid(y=data, sr=sample_rate)
    
    # Total: 80 + 24 + 2 + 2 + 2 = 110 features
    features = np.hstack([
        np.mean(mfcc, axis=1), np.std(mfcc, axis=1),
        np.mean(chroma, axis=1), np.std(chroma, axis=1),
        np.mean(zcr), np.std(zcr),
        np.mean(rms), np.std(rms),
        np.mean(centroid), np.std(centroid)
    ])
    return features

def analisar_tom_de_voz(audio_data_wav):
    """
    Analisa os dados de áudio WAV para detectar uma emoção usando um modelo pré-treinado.
    """
    try:
        # Carrega o modelo pré-treinado do arquivo
        modelo = joblib.load("modelo_emocoes_voz.joblib")

        # Converte os dados de áudio em um formato que o librosa possa ler
        data, sample_rate = soundfile.read(io.BytesIO(audio_data_wav))
        
        # Extrai as características do áudio
        features = extrair_features(data, sample_rate)
        
        # Usa o modelo para prever a emoção
        # O .reshape(1, -1) é necessário para formatar os dados para o modelo
        resultado = modelo.predict(features.reshape(1, -1))
        
        # Retorna a emoção prevista (ex: 'feliz', 'triste', 'neutro')
        return resultado[0]

    except FileNotFoundError:
        print("AVISO: Arquivo 'modelo_emocoes_voz.joblib' não encontrado. Análise de tom de voz desativada.")
        return "neutro" # Retorna neutro se o modelo não for encontrado
    except Exception as e:
        print(f"Erro na análise de tom de voz real: {e}")
        return "neutro" # Retorna um valor seguro em caso de outro erro

def carregar_memoria():
    try:
        with open("memoria_jarvis.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar_memoria(memoria):
    with open("memoria_jarvis.json", "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=4)



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
        resposta_modelo = modelo.chat.completions.create(
            model="gpt-4o",
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


# NOVO carregar_chats
def carregar_chats(username):
    """Carrega os chats de um arquivo JSON específico do usuário."""
    if not username:
        return {} # Retorna um dicionário vazio se não houver nome de usuário

    filename = f"chats_historico_{username}.json"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} # Se o arquivo do usuário não existir, retorna um histórico vazio.


# NOVO salvar_chats
def salvar_chats(username):
    """Salva os chats do usuário em um arquivo JSON específico para ele."""
    if not username:
        return # Não faz nada se não houver um nome de usuário

    filename = f"chats_historico_{username}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(st.session_state.chats, f, ensure_ascii=False, indent=4)


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


def responder_com_inteligencia(pergunta_usuario, modelo, historico_chat, resumo_contexto="", tom_de_voz_detectado=None):
    """
    Decide como responder, considerando memória local, busca na web, preferências e o tom do usuário.
    """
    # =======================================================
    # === CORREÇÃO: Definindo a variável no início ===
    # =======================================================
    # Detecta o idioma da pergunta do usuário para usar em toda a função
    idioma_da_pergunta = detectar_idioma(pergunta_usuario)
    # =======================================================

    # ETAPA 1: Tenta responder com a memória local primeiro
    if modelo_embedding:
        try:
            vetor_pergunta_usuario = modelo_embedding.encode([pergunta_usuario])
            scores_similaridade = cosine_similarity(vetor_pergunta_usuario, vetores_perguntas)
            indice_melhor_match = np.argmax(scores_similaridade)
            score_maximo = scores_similaridade[0, indice_melhor_match]
            LIMIAR_CONFIANCA = 0.8

            if score_maximo > LIMIAR_CONFIANCA:
                logging.info(f"Resposta encontrada na memória local com confiança de {score_maximo:.2%}.")
                st.info(f"Resposta encontrada na memória local (Confiança: {score_maximo:.2%}) 🧠")
                respostas_possiveis = base_de_conhecimento['respostas'][indice_melhor_match]
                resposta_local = random.choice(respostas_possiveis)['texto']
                return {"texto": resposta_local, "origem": "local"}
            
        except Exception as e:
            logging.error(f"Erro ao processar com modelo local: {e}")
            st.warning(f"Erro ao processar com modelo local: {e}. Usando OpenAI.")
    
    # Carrega as preferências do usuário
    username = st.session_state.get("username", "default")
    preferencias = carregar_preferencias(username)
    
    # Detecta o tom do usuário
    tom_do_usuario = detectar_tom_usuario(pergunta_usuario)
    if tom_do_usuario:
        st.sidebar.info(f"Tom detectado: {tom_do_usuario}")

    # ETAPA 2: Decide se precisa de informações da internet
    if precisa_buscar_na_web(pergunta_usuario):
        
        logging.info(f"Iniciando busca na web para a pergunta: '{pergunta_usuario}'")
        
        st.info("Buscando informações em tempo real na web... 🌐")
        contexto_da_web = buscar_na_internet(pergunta_usuario)
        
        prompt_sistema = f"""
        Você é Jarvis, um assistente prestativo.
        INFORMAÇÕES SOBRE SEU USUÁRIO, ISRAEL: {json.dumps(preferencias, ensure_ascii=False)}
        O tom atual do usuário parece ser: {tom_do_usuario}. Adapte o estilo da sua resposta a este tom.

        Sua tarefa é responder à pergunta do usuário de forma clara e direta, baseando-se ESTRITAMENTE nas informações de contexto que foram coletadas da internet.
        
        Contexto da Web:
        {contexto_da_web}
        """

    else:
        # ETAPA 3: Se não precisa de busca, usa o fluxo de chat padrão
        logging.info("Pergunta não requer busca na web, consultando a OpenAI.")
        st.info("Consultando a OpenAI...")
        
        prompt_sistema = "Você é Jarvis, um assistente prestativo."
        
        if tom_de_voz_detectado and tom_de_voz_detectado != "neutro":
            prompt_sistema += f"\nO tom de voz do usuário parece ser '{tom_de_voz_detectado}'. Adapte sua resposta a isso, sendo mais empático ou cuidadoso se necessário."
        if tom_do_usuario:
            prompt_sistema += f"\nO tom do texto dele parece ser '{tom_do_usuario}'. Adapte seu estilo de resposta a isso (ex: se ele estiver apressado, seja breve; se estiver descontraído, seja mais amigável)."
        if preferencias:
            prompt_sistema += f"\nLembre-se destas preferências sobre seu usuário, Israel: {json.dumps(preferencias, ensure_ascii=False)}"
        if resumo_contexto:
            prompt_sistema += f"\nLembre-se também do contexto da conversa atual: {resumo_contexto}"
        
    # =======================================================
    # === CORREÇÃO: Adicionando a instrução de idioma ao final do prompt ===
    # =======================================================
    prompt_sistema += f"\n\nIMPORTANTE: Responda ao usuário final estritamente no seguinte idioma, sem exceções: '{idioma_da_pergunta}'"
    # =======================================================

    mensagens_para_api = [{"role": "system", "content": prompt_sistema}]
    mensagens_para_api.extend(historico_chat)

    # Chamada final para a OpenAI
    resposta_modelo = modelo.chat.completions.create(
        messages=mensagens_para_api,
        model="gpt-4o"
    )
    resposta_ia = resposta_modelo.choices[0].message.content
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


def escutar_audio():
    idioma_para_reconhecimento = st.session_state.get("idioma_fala", "pt-BR")
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.info(f"Fale agora (em {idioma_para_reconhecimento})...")
            recognizer.adjust_for_ambient_noise(source)
            audio_capturado = recognizer.listen(source)

        st.info("Processando áudio...")

        # Etapa 1: Transcrever o texto
        texto_reconhecido = recognizer.recognize_google(
            audio_capturado, language=idioma_para_reconhecimento)
        st.success("Áudio transcrito!")

        # Etapa 2: Analisar o tom de voz
        tom_de_voz = analisar_tom_de_voz(audio_capturado.get_wav_data())
        st.info(f"Tom de voz detectado (exemplo): {tom_de_voz}")

        # Etapa 3: Retornar AMBOS os resultados
        return texto_reconhecido, tom_de_voz

    except sr.UnknownValueError:
        st.warning("Não consegui entender o que você disse.")
        # Retorna DOIS valores em caso de erro
        return None, None
    except sr.RequestError as e:
        st.error(f"Não foi possível se conectar ao serviço de reconhecimento; {e}")
        # Retorna DOIS valores em caso de erro
        return None, None
    except Exception as e:
        st.error(f"Ocorreu um erro ao acessar o microfone: {e}")
        print(f"ERRO DETALHADO DO MICROFONE: {e}")
        # Retorna DOIS valores em caso de erro
        return None, None


def processar_entrada_usuario(prompt_usuario, tom_voz=None):
    chat_id = st.session_state.current_chat_id
    active_chat = st.session_state.chats[chat_id]

    # Prepara o histórico da conversa
    historico_chat = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in active_chat["messages"]
        if msg.get("type") == "text"
    ]

    # --- LÓGICA DA MEMÓRIA DE CURTO PRAZO ---
    numero_de_mensagens = len(historico_chat)
    if numero_de_mensagens > 0 and numero_de_mensagens % 6 == 0:
        resumo_atualizado = gerar_resumo_curto_prazo(historico_chat)
        active_chat["resumo_curto_prazo"] = resumo_atualizado
        st.toast("🧠 Memória de curto prazo atualizada.", icon="🔄")

    resumo_contexto = active_chat.get("resumo_curto_prazo", "")

    # --- LÓGICA DE ANÁLISE DE DOCUMENTOS (REINTEGRADA) ---
    contexto_do_arquivo = active_chat.get("contexto_arquivo")

    if contexto_do_arquivo:
        historico_para_analise = [
            {"role": "system", "content": "Você é um assistente especialista em análise de dados e documentos. Responda às perguntas do usuário baseando-se ESTRITAMENTE no conteúdo do documento fornecido abaixo."},
            {"role": "user", "content": f"CONTEÚDO DO DOCUMENTO PARA ANÁLISE:\n---\n{contexto_do_arquivo}\n---"},
            {"role": "assistant", "content": "Entendido. O conteúdo do documento foi carregado. Estou pronto para responder suas perguntas sobre ele."}
        ]
        historico_para_analise.extend(historico_chat)
        historico_final = historico_para_analise
    else:
        historico_final = historico_chat

    # Chama a função de resposta com o histórico final e o tom da voz
    dict_resposta = responder_com_inteligencia(
        prompt_usuario, modelo, historico_final, resumo_contexto, tom_de_voz_detectado=tom_voz)

    # Adiciona a resposta da IA ao histórico
    active_chat["messages"].append({
        "role": "assistant",
        "type": "text",
        "content": dict_resposta["texto"],
        "origem": dict_resposta["origem"]
    })
    salvar_chats(st.session_state["username"])
    st.rerun()


def adicionar_a_memoria(pergunta, resposta):
    """Adiciona um novo par de pergunta/resposta à memória local."""
    try:
        memoria_atual = carregar_memoria()
        # Usa a função que já temos para classificar a categoria
        categoria = classificar_categoria(pergunta)

        nova_entrada = {
            "pergunta": pergunta,
            "respostas": [{"texto": resposta, "tom": "neutro"}]
        }

        if categoria not in memoria_atual:
            memoria_atual[categoria] = []

        # Evita adicionar duplicatas exatas
        if not any(item["pergunta"].lower() == pergunta.lower() for item in memoria_atual[categoria]):
            memoria_atual[categoria].append(nova_entrada)
            salvar_memoria(memoria_atual)
            st.toast("✅ Memória atualizada com sucesso!", icon="🧠")
        else:
            st.toast("Essa pergunta já existe na memória.", icon="💡")

    except Exception as e:
        st.error(f"Erro ao salvar na memória: {e}")


def gerar_resumo_curto_prazo(historico_chat):
    """Gera um resumo da conversa recente usando a OpenAI."""
    print("Gerando resumo de curto prazo...")

    # Pega as últimas 10 mensagens para não sobrecarregar o prompt
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
        resposta_modelo = modelo.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )
        resumo = resposta_modelo.choices[0].message.content.strip()
        return resumo
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        return ""  # Retorna vazio em caso de erro

# NOVA FUNÇÃO 1: O "DETECTOR DE ATUALIDADES"


def precisa_buscar_na_web(pergunta_usuario):
    """
    Usa a OpenAI para decidir rapidamente se uma pergunta requer busca na web.
    """
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
        resposta_modelo = modelo.chat.completions.create(
            model="gpt-4o",
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


# NOVA FUNÇÃO 2: A FERRAMENTA DE BUSCA
def buscar_na_internet(pergunta_usuario):
    """
    Pesquisa a pergunta na web usando a API Serper e retorna um resumo dos resultados.
    """
    print(f"Pesquisando na web por: {pergunta_usuario}")
    #api_key_serper = os.getenv("SERPER_API_KEY")
    #api_key_serper = st.secrets["SERPER_API_KEY"]
    if not api_key_serper:
        return "ERRO: A chave da API Serper não foi configurada."

    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": pergunta_usuario, "gl": "br", "hl": "pt-br"})
    headers = {'X-API-KEY': api_key_serper, 'Content-Type': 'application/json'}

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        resultados = response.json().get('organic', [])

        if not resultados:
            return "Nenhum resultado encontrado na web."

        # Pega os 3 principais resultados para montar o contexto
        contexto_web = []
        for i, item in enumerate(resultados[:3]):
            titulo = item.get('title', 'Sem título')
            snippet = item.get('snippet', 'Sem descrição')
            contexto_web.append(f"Fonte {i+1} ({titulo}): {snippet}")

        return "\n".join(contexto_web)
    except Exception as e:
        return f"ERRO ao pesquisar na web: {e}"


# --- INTERFACE GRÁFICA (STREAMLIT) ---
st.set_page_config(page_title="Jarvis IA", layout="wide")
st.markdown("""<style>.stApp { background-color: #0d1117; color: #c9d1d9; } .stTextInput, .stChatInput textarea { background-color: #161b22; color: #c9d1d9; border-radius: 8px; } .stButton button { background-color: #151b22; color: white; border-radius: 10px; border: none; }</style>""", unsafe_allow_html=True)

memoria = carregar_memoria()

# --- GESTÃO DE CHATS ---


def create_new_chat():
    """Cria um novo chat com os campos necessários, incluindo a memória de curto prazo."""
    chat_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    st.session_state.chats[chat_id] = {
        "title": "Jarvis IA - Welcome!",
        "messages": [],
        "contexto_arquivo": "",
        "ultima_mensagem_falada": None,
        "processed_file_name": None,
        "resumo_curto_prazo": ""  # NOVO: Campo para a memória de curto prazo
    }
    st.session_state.current_chat_id = chat_id
    
    return chat_id


def switch_chat(chat_id):
    st.session_state.current_chat_id = chat_id


def delete_chat(chat_id_to_delete):
    if chat_id_to_delete in st.session_state.chats:
        del st.session_state.chats[chat_id_to_delete]
        
        # Se o chat deletado era o chat atual, mude para outro chat ou crie um novo
        if st.session_state.current_chat_id == chat_id_to_delete:
            if st.session_state.chats: # Se ainda existirem outros chats
                st.session_state.current_chat_id = list(st.session_state.chats.keys())[-1]
            else: # Se não houver mais chats, crie um novo
                create_new_chat()
        
        # Garante que o estado atualizado seja salvo no arquivo
        salvar_chats(st.session_state["username"])
        
        st.rerun() # Recarrega a aplicação para refletir a mudança


# --- INICIALIZAÇÃO E SIDEBAR ---
if "chats" not in st.session_state:
    st.session_state.chats = carregar_chats(st.session_state["username"])
    if not st.session_state.chats:
        create_new_chat()
    if "current_chat_id" not in st.session_state or st.session_state.current_chat_id not in st.session_state.chats:
        st.session_state.current_chat_id = list(
            st.session_state.chats.keys())[-1]

chat_id = st.session_state.current_chat_id
active_chat = st.session_state.chats[chat_id]

with st.sidebar:
    st.write("### 🤖 Jarvis IA")

    # --- NAVEGAÇÃO CUSTOMIZADA DA SIDEBAR ---
    st.sidebar.title("Navegação")

    # Link para a página principal, visível para todos
    st.sidebar.page_link("app.py", label="Chat Principal", icon="🤖")
    
        # --- NOVA SEÇÃO PARA O USUÁRIO LOGADO ---
    st.sidebar.divider()
    st.sidebar.header("Painel do Usuário")
    # Este link aparecerá para QUALQUER usuário logado
    st.sidebar.page_link("pages/3_Gerenciar_Preferencias.py", label="Minhas Preferências", icon="⚙️")
    # --- FIM DA NOVA SEÇÃO ---

    # Verifica se o usuário logado é o admin para mostrar as páginas restritas
    #if st.session_state.get("username") == ADMIN_USERNAME:
      #  st.sidebar.divider()
       # st.sidebar.header("Painel do Admin")
        
        # Links para as páginas de admin, usando os nomes exatos dos seus arquivos
       # st.sidebar.page_link("pages/1_Gerenciar_Memoria.py", label="Gerenciar Memória", icon="🧠")
       # st.sidebar.page_link("pages/2_Status_do_Sistema.py", label="Status do Sistema", icon="📊")
    
    st.sidebar.divider()
    
    
    # --- AÇÕES E HISTÓRICO ---
    
    # Seção de Ações Principais
    if st.button("➕ Novo Chat", use_container_width=True, type="primary"):
        create_new_chat()
        st.rerun()

    voz_ativada = st.checkbox(
        "🔊 Ouvir respostas do Jarvis", value=False, key="voz_ativada")
    st.divider()

    st.write("#### Configurações de Voz")
    idioma_selecionado = st.selectbox(
        "Idioma da Fala (Entrada)",
        options=['pt-BR', 'en-US', 'es-ES', 'fr-FR', 'de-DE', 'it-IT'], # Sinta-se à vontade para adicionar mais
        index=0, # Garante que 'pt-BR' seja o padrão
        key="idioma_fala",
        help="Escolha o idioma que você irá falar no microfone."
    )

    # Seção do Histórico de Chats
    st.write("#### Histórico de Chats")
    # Garante que o st.session_state.chats existe antes de iterar
    if "chats" in st.session_state:
        for id, chat_data in reversed(list(st.session_state.chats.items())):
            col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
            with col1:
                if st.button(chat_data["title"], key=f"chat_{id}", use_container_width=True, type="secondary" if id != st.session_state.current_chat_id else "primary"):
                    switch_chat(id)
                    st.rerun()
            with col2:
                with st.popover("✏️", use_container_width=True):
                    new_title = st.text_input(
                        "Novo título:", value=chat_data["title"], key=f"rename_input_{id}")
                    if st.button("Salvar", key=f"save_rename_{id}"):
                        st.session_state.chats[id]["title"] = new_title
                        salvar_chats(st.session_state["username"])
                        st.rerun()
            with col3:
                with st.popover("🗑️", use_container_width=True):
                    st.write(
                        f"Tem certeza que deseja excluir '{chat_data['title']}'?")
                    if st.button("Sim, excluir!", type="primary", key=f"delete_confirm_{id}"):
                        delete_chat(id)
    st.divider()

    # Seção para Anexar Arquivos
    with st.expander("📂 Anexar Arquivos"):
        # ATUALIZE ESTA LISTA COM AS NOVAS EXTENSÕES PARA O FILE_UPLOADER
        tipos_aceitos = [
            "pdf", "docx", "txt", "xlsx", "xls",
            "py", "js", "ts", "html", "htm", "css", "php", "java", "kt",
            "c", "cpp", "h", "cs", "rb", "go", "swift", "sql", "json",
            "xml", "yaml", "yml", "md", "sh", "bat", "ps1", "R", "pl", "lua"
        ]
        # Usa um chat_id como parte da chave para garantir que o uploader reinicie com o chat
        chat_id_for_key = st.session_state.current_chat_id
        
        arquivo = st.file_uploader(
            "📄 Documento, Planilha ou Arquivo de Código", # Rótulo do uploader
            type=tipos_aceitos, # <-- AGORA USARÁ A LISTA COMPLETA
            key=f"uploader_doc_{chat_id_for_key}"
        )
        if arquivo and arquivo.name != st.session_state.chats[chat_id_for_key].get("processed_file_name"):
            st.session_state.chats[chat_id_for_key]["contexto_arquivo"] = extrair_texto_documento(arquivo)
            st.session_state.chats[chat_id_for_key]["processed_file_name"] = arquivo.name
            salvar_chats(st.session_state["username"])
            st.rerun()

        imagem = st.file_uploader(
            "🖼️ Imagem", type=["png", "jpg", "jpeg"], key=f"uploader_img_{chat_id_for_key}")
        if imagem and imagem.name != st.session_state.chats[chat_id_for_key].get("processed_file_name"):
            st.image(imagem, width=200)
            st.session_state.chats[chat_id_for_key]["contexto_arquivo"] = analisar_imagem(imagem)
            st.session_state.chats[chat_id_for_key]["processed_file_name"] = imagem.name
            salvar_chats(st.session_state["username"])
            st.rerun()
            
        if active_chat.get("contexto_arquivo"):
            st.info("Jarvis está em 'Modo de Análise de Dados'.")
            st.text_area("Conteúdo extraído:",
                         value=active_chat["contexto_arquivo"], height=150, key=f"context_area_{chat_id}")
            if st.button("🗑️ Esquecer Arquivo Atual", type="primary", key=f"forget_btn_{chat_id}"):
                create_new_chat()
                st.rerun()
    
    # Detecta se estamos na nuvem verificando a existência de um "Secret"
    # Se o secret existir, estamos na nuvem.
    IS_CLOUD_ENV = "OPENAI_API_KEY" in st.secrets # This line is correct

    # SÓ MOSTRA O BOTÃO DO MICROFONE AQUI DENTRO DO `with st.sidebar:`
    if not IS_CLOUD_ENV:
        if st.button("🎙️Falar", key=f"mic_btn_{chat_id}"):
            texto_audio, tom_da_voz = escutar_audio()
            
            if texto_audio:
                # Passo 1: Adiciona a pergunta do usuário ao histórico para exibição imediata
                chat_id = st.session_state.current_chat_id
                active_chat = st.session_state.chats[chat_id]
                active_chat["messages"].append(
                    {"role": "user", "type": "text", "content": texto_audio})

                # Salva o chat imediatamente para garantir que a pergunta apareça
                salvar_chats(st.session_state["username"])
                
                # Passo 2: Agora sim, processa a entrada para gerar a resposta do Jarvis
                processar_entrada_usuario(texto_audio, tom_voz=tom_da_voz)
    else:
        # Opcional: Mostra um aviso útil para o usuário na versão web
        st.sidebar.warning("A função de microfone (falar) está desativada na versão web.", icon="🎙️")


# --- ÁREA PRINCIPAL DO CHAT ---
st.write(f"### {active_chat['title']}")

for i, mensagem in enumerate(active_chat["messages"]):
    with st.chat_message(mensagem["role"]):
        # Lógica para exibir imagens ou texto
        if mensagem.get("type") == "image":
            st.image(mensagem["content"], caption=mensagem.get(
                "prompt", "Imagem gerada"))
        else:
            st.write(mensagem["content"])

# ... no loop principal de chat
# Verifica se a mensagem veio da OpenAI E SE o usuário logado é o admin
        if mensagem.get("origem") == "openai" and st.session_state.get("username") == ADMIN_USERNAME:
            # Pega a pergunta do usuário que gerou esta resposta
            pergunta_original = active_chat["messages"][i-1]["content"]
            resposta_original = mensagem["content"]

            # Cria colunas para alinhar os ícones dos botões
            cols = st.columns([1, 1, 10])  # A última coluna é um espaçador

            # Coluna 1: Botão Salvar
            with cols[0]:
                if st.button("✅", key=f"save_{i}", help="Salvar resposta na memória"):
                    adicionar_a_memoria(pergunta_original, resposta_original)
                    mensagem["origem"] = "openai_curado"
                    salvar_chats(st.session_state["username"])
                    st.rerun()

            # Coluna 2: Botão Editar (com Popover)
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
                                pergunta_editada, resposta_editada)
                            mensagem["origem"] = "openai_curado"
                            salvar_chats(st.session_state["username"])
                            st.rerun()

# Lógica de Text-to-Speech (continua aqui)
if active_chat["messages"] and active_chat["messages"][-1]["role"] == "assistant" and voz_ativada:
    if active_chat["messages"][-1].get("type") == "text":
        resposta_ia = active_chat["messages"][-1]["content"]
        if resposta_ia != active_chat.get("ultima_mensagem_falada"):
            idioma_detectado = detectar_idioma(resposta_ia)
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

if active_chat["messages"] and active_chat["messages"][-1]["role"] == "assistant" and voz_ativada:
    if active_chat["messages"][-1].get("type") == "text":
        resposta_ia = active_chat["messages"][-1]["content"]
        if resposta_ia != active_chat.get("ultima_mensagem_falada"):
            idioma_detectado = detectar_idioma(resposta_ia)
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

# --- Bloco para Exibição Persistente do Botão de Download ---
# Ele verifica em toda recarga se deve mostrar o botão.
if 'pdf_para_download' in st.session_state:
    with st.chat_message("assistant"):
        st.download_button(
            label="📥 Baixar PDF",
            data=st.session_state['pdf_para_download'],
            file_name=st.session_state['pdf_filename'],
            mime="application/pdf",
            on_click=limpar_pdf_da_memoria  # <-- A MÁGICA ACONTECE AQUI
        )

# --- ENTRADA DE TEXTO DO USUÁRIO ---
if prompt_usuario := st.chat_input("Fale com a Jarvis ou use /lembrese, /imagine, /pdf..."):

    # Adiciona a mensagem do usuário ao histórico para exibição imediata
    active_chat["messages"].append(
        {"role": "user", "type": "text", "content": prompt_usuario})

    # Salva o chat imediatamente após adicionar a mensagem do usuário
    salvar_chats(st.session_state["username"])

    # --- PROCESSAMENTO DE COMANDOS ESPECIAIS ---
    # A estrutura if/elif/else a seguir está CORRETAMENTE aninhada.
    if prompt_usuario.lower().startswith("/lembrese "):
        texto_para_lembrar = prompt_usuario[10:].strip()
        if texto_para_lembrar:
            with st.chat_message("assistant"):
                st.info("Memorizando sua preferência...")
                processar_comando_lembrese(texto_para_lembrar)

    elif prompt_usuario.lower().startswith("/imagine "):
        prompt_da_imagem = prompt_usuario[9:].strip()
        if prompt_da_imagem:
            with st.chat_message("assistant"):
                url_da_imagem = gerar_imagem_com_dalle(prompt_da_imagem)
                if url_da_imagem:
                    active_chat["messages"].append(
                        {"role": "assistant", "type": "image", "content": url_da_imagem, "prompt": prompt_da_imagem})
                    salvar_chats(st.session_state["username"])
            st.rerun()

    elif prompt_usuario.lower().startswith("/pdf "):
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

    else:
        # Se não for nenhum comando, chama a função de processamento de chat normal
        processar_entrada_usuario(prompt_usuario)