import os
import numpy as np
import librosa
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
import joblib
# --- NOVA IMPORTAÇÃO ---
from sklearn.preprocessing import StandardScaler

# Caminho da pasta com os áudios
PASTA_AUDIO = "dados_audio_jarvis"

# Emoções que você quer reconhecer (devem corresponder aos nomes das subpastas)
EMOCOES = ['feliz', 'triste', 'raiva', 'neutro']

# Função para extrair features (continua a mesma)
def extrair_features(audio_path):
    try:
        y, sr = librosa.load(audio_path, sr=None)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        zcr = librosa.feature.zero_crossing_rate(y)
        rms = librosa.feature.rms(y=y)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        
        features = np.hstack([
            np.mean(mfcc, axis=1), np.std(mfcc, axis=1),
            np.mean(chroma, axis=1), np.std(chroma, axis=1),
            np.mean(zcr), np.std(zcr),
            np.mean(rms), np.std(rms),
            np.mean(centroid), np.std(centroid)
        ])
        return features
    except Exception as e:
        print(f"Erro ao processar {audio_path}: {e}")
        return None

# --- Bloco de Coleta de Dados (continua o mesmo) ---
X = []
y = []
print("Iniciando a extração de features dos arquivos de áudio...")
for root, dirs, files in os.walk(PASTA_AUDIO):
    for arquivo in files:
        if arquivo.endswith(".wav"):
            emocao = os.path.basename(root)
            if emocao in EMOCOES:
                caminho_completo = os.path.join(root, arquivo)
                print(f"Processando: {caminho_completo}")
                feats = extrair_features(caminho_completo)
                if feats is not None and feats.shape[0] == 110:
                    X.append(feats)
                    y.append(emocao)
                elif feats is not None:
                    print(f"  AVISO: O arquivo {arquivo} gerou um número inesperado de features ({feats.shape[0]}). Ignorando.")
print(f"\nExtração concluída. Total de {len(X)} amostras encontradas.")

# --- Bloco de Treinamento ---
if not X:
    print("\nERRO: Nenhuma amostra foi carregada. Verifique a estrutura das pastas e os arquivos de áudio. Encerrando.")
else:
    X = np.array(X)
    y = np.array(y)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- PIPELINE MELHORADO ---
    # Adicionamos o 'StandardScaler' para normalizar os dados antes do treino.
    # Ajustamos o 'C' e 'gamma' do SVM para valores que costumam funcionar bem.
    modelo = Pipeline([
        ('scaler', StandardScaler()),  # <-- PASSO 1: Normalização
        ('svm', SVC(C=10, gamma=0.001, probability=True, kernel='rbf')) # <-- PASSO 2: Ajuste de Hiperparâmetros
    ])

    print("\nIniciando o treinamento do modelo...")
    modelo.fit(X_train, y_train)
    print("Treinamento concluído.")

    acuracia = modelo.score(X_test, y_test)
    print(f"\nAcurácia do modelo no conjunto de teste: {acuracia:.2%}")

    nome_modelo_salvo = "modelo_emocoes_voz.joblib"
    joblib.dump(modelo, nome_modelo_salvo)
    print(f"\n✅ Modelo salvo com sucesso: {nome_modelo_salvo}")