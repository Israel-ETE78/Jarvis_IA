# 🤖 Jarvis IA – Sua Inteligência Artificial Pessoal

Jarvis IA é um sistema inteligente e personalizável, criado para funcionar como um **assistente pessoal com voz, memória e aprendizado contínuo**. Desenvolvido com foco em programadores, estudantes e entusiastas de tecnologia, ele roda diretamente no navegador com suporte local e na nuvem.

---

## 🚀 Funcionalidades Principais

- 🧠 **Chat com inteligência adaptativa** (GPT-3.5 / GPT-4 / GPT-4o)
- 🗣️ **Resposta por voz com fala natural**
- 📂 **Leitura e análise de arquivos** (PDF, CSV, DOCX, JSON, imagens, códigos, etc.)
- 🖼️ **Criação de imagens por IA**
- 🧾 **Geração de PDFs personalizados**
- 🗃️ **Memória local inteligente por preferências**
- 🧑‍🎓 **Assistente de análise de dados com gráficos**
- 🌐 **Modo multilíngue**: Entende e responde em vários idiomas
- 📜 **Sistema de lembretes com voz**
- 🔐 **Modo Sentinela (privacidade ativa por padrão)**
- 📊 **Painel administrativo de assinaturas (Supabase ou JSON local)**

---

## 📁 Estrutura do Projeto

```
📦 jarvis_ia/
├── app.py                       # Arquivo principal do app
├── utils.py                     # Funções auxiliares (banco, preferências, etc)
├── auth.py                      # Sistema de login e senha
├── treinar_memoria.py           # Treinamento da memória vetorial
├── pages/
│   ├── 1_Gerenciar_Memoria.py   # (Admin) Gerenciar memória inteligente
│   ├── 2_Status_do_Sistema.py   # (Admin) Logs e status
│   ├── 3_Gerenciar_Preferencias.py # Preferências do usuário
│   ├── 4_Lembretes.py           # Sistema de lembretes com voz
│   └── 5_Assinaturas.py         # Painel de controle de assinaturas
├── dados/                       # Memórias, históricos e backups
│   ├── memoria_jarvis.json
│   ├── preferencias_israel.json
│   └── chats_historico_*.json
├── .env                         # Variáveis locais (não subir para GitHub)
├── requirements.txt             # Dependências do projeto
├── README.md                    # Este arquivo
```

---

## 🛠️ Requisitos

- Python 3.10+
- Streamlit
- OpenAI SDK
- Supabase (opcional)
- API Serper (opcional para buscas web)
- Voz: SpeechRecognition + PyAudio (local)

**Instale tudo com:**

```bash
pip install -r requirements.txt
```

---

## 🔐 Variáveis de Ambiente

Adicione ao `.env` ou `secrets.toml` no Streamlit Cloud:

```ini
OPENAI_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
EMAIL_REMETENTE=...
EMAIL_SENHA_APP=...
EMAIL_ADMIN=...
SERPER_API_KEY=...
ADMIN_USERNAME=israel
```

---

## 🧪 Teste Grátis (Exemplo de Divulgação)

```
🌐 https://jarvis-ia.streamlit.app/

👤 Usuário: etecicerodias
🔐 Senha:   Nave@2025
```

---

## 🧑‍💼 Recursos para o Usuário

- `/lembrese`: salva preferências personalizadas
- `/resumo`: gera um resumo de PDFs e textos
- `/imagem`: cria imagens com base no texto
- `/pdf`: gera arquivos em PDF com formatação
- `/voz`: ativa/desativa fala
- `/dados`: ativa o modo de análise de CSV e Excel

---

## 📬 Feedback e Suporte

- Envie sugestões direto pela aba lateral "💬 Feedback"
- Suporte por e-mail: **jarvisiasuporte@gmail.com**

---

## 📢 Sobre o Criador

Desenvolvido por **Israel Paz**  
Estudante de Desenvolvimento de Sistemas • Graduado em Redes de Computadores  
Objetivo: Criar uma IA real, ética, segura e personalizada.

---

## 📜 Licença

Este projeto é de uso educacional e experimental. Proibida a revenda ou distribuição não autorizada. Todos os direitos reservados.