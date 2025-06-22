# treinar_memoria.py - VERSÃO 2.0 com Sentence Transformers

import json
import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

print(">> INICIANDO O CENTRO DE TREINAMENTO AVANÇADO DO JARVIS <<")

def carregar_dados_de_treinamento():
    """Lê o arquivo memoria_jarvis.json e extrai as perguntas e respostas."""
    try:
        with open("memoria_jarvis.json", "r", encoding="utf-8") as f:
            memoria = json.load(f)
        
        perguntas = []
        respostas = []
        for categoria in memoria.values():
            for item in categoria:
                if 'pergunta' in item and 'respostas' in item and item['respostas']:
                    perguntas.append(item['pergunta'])
                    respostas.append(item['respostas'])
        
        if not perguntas:
            print("AVISO: 'memoria_jarvis.json' está vazio ou não tem o formato esperado. Nenhum modelo será treinado.")
            return None, None
            
        print(f"Encontradas {len(perguntas)} perguntas na memória para o treinamento.")
        return perguntas, respostas

    except FileNotFoundError:
        print("ERRO: Arquivo 'memoria_jarvis.json' não encontrado.")
        return None, None
    except json.JSONDecodeError:
        print("ERRO: O arquivo 'memoria_jarvis.json' está mal formatado.")
        return None, None

perguntas_treino, respostas_associadas = carregar_dados_de_treinamento()

if perguntas_treino and respostas_associadas:
    print("Carregando o modelo de embedding multilíngue (pode levar um momento e baixar dados no primeiro uso)...")
    modelo_embedding = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    print("Vectorizando as perguntas (criando 'impressões digitais' semânticas)...")
    vetores_de_perguntas = modelo_embedding.encode(perguntas_treino, show_progress_bar=True)
    
    print("Salvando os artefatos do cérebro treinado...")
    base_de_conhecimento = {
        "perguntas": perguntas_treino,
        "respostas": respostas_associadas
    }
    joblib.dump(base_de_conhecimento, 'dados_conhecimento_v2.joblib')
    np.save('vetores_perguntas_v2.npy', vetores_de_perguntas)
    
    print("\n>> TREINAMENTO AVANÇADO CONCLUÍDO COM SUCESSO! <<")
    print("O cérebro de reflexos do Jarvis foi aprimorado e salvo nos seguintes arquivos:")
    print("- dados_conhecimento_v2.joblib")
    print("- vetores_perguntas_v2.npy")