import json
from datetime import datetime
import os

# Suponha que você tenha uma função para enviar e-mails
# from seu_modulo_email import enviar_email 

def verificar_todos_os_lembretes():
    print("Iniciando o script verificador de lembretes...")
    print(f"Verificação iniciada em: {datetime.now()}")

    try:
        with open('assinaturas.json', 'r', encoding='utf-8') as f:
            assinaturas = json.load(f)
        print(f"Carregadas {len(assinaturas)} assinaturas.")
    except FileNotFoundError:
        print("ERRO: Arquivo 'assinaturas.json' não encontrado.")
        return
    except json.JSONDecodeError:
        print("ERRO: Arquivo 'assinaturas.json' está mal formatado.")
        return

    # 2. Iniciar o Loop por cada usuário
    for usuario_info in assinaturas:
        # Pula usuários que não estão ativos
        if usuario_info.get('status') != 'ativo':
            continue

        username = usuario_info.get('username')
        email_usuario = usuario_info.get('email')

        if not username or not email_usuario:
            print(f"AVISO: Registro de assinatura incompleto, pulando: {usuario_info}")
            continue

        print(f"\n--- Verificando lembretes para o usuário: '{username}' ---")

        # 3. Construir o caminho para o arquivo de lembretes do usuário
        caminho_lembretes = os.path.join('dados', 'lembretes', f'chats_historico_{username}.json')
        
        try:
            with open(caminho_lembretes, 'r', encoding='utf-8') as f:
                lembretes_do_usuario = json.load(f)
        except FileNotFoundError:
            print(f"Nenhum arquivo de lembretes encontrado para '{username}'. Pulando.")
            continue
        except json.JSONDecodeError:
            print(f"ERRO: Arquivo de lembretes para '{username}' está mal formatado.")
            continue
            
        lembretes_modificados = False
        
        # 4. Processar cada lembrete individualmente
        for lembrete in lembretes_do_usuario:
            status = lembrete.get('status', '').lower()
            
            if status == 'pendente':
                try:
                    # Adapte o formato da data se for diferente
                    data_lembrete = datetime.fromisoformat(lembrete['data_lembrete'])
                    
                    # 5. Se estiver na hora, enviar o e-mail
                    if datetime.now() >= data_lembrete:
                        print(f"  -> Lembrete encontrado: '{lembrete['titulo']}'. Enviando para {email_usuario}...")
                        
                        # ################################################
                        # # AQUI VOCÊ CHAMA SUA FUNÇÃO DE ENVIAR E-MAIL  #
                        # sucesso = enviar_email(
                        #     destinatario=email_usuario,
                        #     assunto=f"Lembrete: {lembrete['titulo']}",
                        #     corpo=f"Olá {username}, este é um lembrete para: {lembrete['titulo']}."
                        # )
                        # ################################################
                        sucesso = True # Simulação de sucesso
                        
                        if sucesso:
                            print("  -> E-mail enviado com sucesso!")
                            # 6. Atualizar o status
                            lembrete['status'] = 'enviado'
                            lembretes_modificados = True
                        else:
                            print("  -> FALHA AO ENVIAR E-MAIL.")

                except (ValueError, KeyError) as e:
                    print(f"  -> AVISO: Lembrete mal formatado ou com data inválida, pulando. Erro: {e}")

        # 7. Se algum lembrete foi alterado, salvar o arquivo de volta
        if lembretes_modificados:
            print(f"Salvando alterações no arquivo de lembretes de '{username}'...")
            with open(caminho_lembretes, 'w', encoding='utf-8') as f:
                json.dump(lembretes_do_usuario, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    verificar_todos_os_lembretes()
    print("\nVerificação de lembretes concluída para todos os usuários.")