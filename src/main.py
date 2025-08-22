import re
import os
import dateparser
from datetime import datetime
from fastapi import FastAPI, Request, Response
from .services.meta_api_client import MetaAPIClient
from .services.google_sheets_api_client import GoogleSheetsAPIClient
from google_auth_oauthlib.flow import Flow
from src.data import db


sheets_client = GoogleSheetsAPIClient()
meta_client = MetaAPIClient()
app = FastAPI()

REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
flow = Flow.from_client_secrets_file(
    sheets_client.CLIENT_SECRET_FILE,
    scopes=sheets_client.SCOPES,
    redirect_uri=REDIRECT_URI
)

@app.get('/webhook/meta')
def auth_webhook(req: Request):
    if req.query_params['hub.mode'] == 'subscribe' and req.query_params['hub.verify_token'] == os.getenv('META_TOKEN_WEBHOOK'):
        return Response(req.query_params['hub.challenge'])
    else:
        return Response(status_code=400)

@app.post('/webhook/meta')
async def process_message(request: Request):
    payload = await request.json()

    try:
        # Navega pela estrutura do JSON da Meta
        changes = payload['entry'][0]['changes'][0]
        if changes['field'] == 'messages':
            message_data = changes['value']['messages'][0]
            number_sender = message_data['from']
            text = message_data['text']['body'].strip()

            print(f"Mensagem de {number_sender}: '{text}'")

            user = db.get_user(number_sender)

            if not user:
                authorization_url, state = flow.authorization_url(access_type='offline', prompt='consent', state=number_sender)

                message = (f"Olá! Para começar, preciso de permissão para acessar suas planilhas.\n\n"
                        f"Clique no link abaixo para autorizar:\n\n{authorization_url}")
                meta_client.send_message(number=number_sender, text=message)

                return {'status': 'auth_started'}
            
            if user and text.lower().startswith('/configurar'):
                try:
                    url = text.split(' ')[1]
                    # Extrai o ID da URL da planilha
                    spreadsheet_id = re.search(r'/d/([a-zA-Z0-9-_]+)', url).group(1)
                    db.save_spreadsheet_id(number_sender, spreadsheet_id)
                    meta_client.send_message(number=number_sender, text="✅ Planilha configurada com sucesso! Agora você já pode fazer seus lançamentos.")
                except (IndexError, AttributeError):
                    meta_client.send_message(number=number_sender, text="Formato inválido. Use: */configurar <URL_DA_SUA_PLANILHA>*")
                return {'status': 'configured'}

            pattern = r'(?i)^(Entrada|Saida|Diario)\s+([\d,.]+)\s+(.+)$'
            m = re.match(pattern, text)

            if not m:
                response_message = "Formato inválido. Use: *Tipo Valor Data* (ex: Saida 25,50 hoje)"
                meta_client.send_message(number=number_sender, text=response_message)
                return {'status': 'invalid_format'}
            
            type, value, date = m.groups()

            date_in_datetime = dateparser.parse(date, languages=['pt'])
            if not date_in_datetime:
                response_message = 'Não consegui entender a data. Ex: "hoje" ou "amanha" ou "31/12/2025"'
                meta_client.send_message(number=number_sender, text=response_message)
                return {'message': 'data inválida'}
            
            try:
                response_message = sheets_client.update_sheet(
                    refresh_token=user['refresh_token'],
                    spreadsheet_id=user['spreadsheet_id'],
                    type=type.capitalize(),
                    value=value,
                    date=date_in_datetime,
                    date_now=datetime.now()
                )
            except Exception as e:
                print(f"Erro ao atualizar planilha: {e}")
                response_message = "Ocorreu um erro ao tentar atualizar sua planilha. Verifique se ela foi compartilhada corretamente ou se o formato está correto."

            meta_client.send_message(number=number_sender, text=response_message)

            return {'status': 'ok'}

    except (KeyError, IndexError) as e:
        # Ignora eventos que não são mensagens de texto (ex: status de entrega)
        print(f"Payload não é uma mensagem de texto ou tem formato inesperado: {e}")
        pass

@app.get('/oauth2callback')
async def oauth2callback(request: Request):
    # O 'state' nos diz qual usuário iniciou o fluxo
    whatsapp_id = request.query_params.get('state')
    
    # Troca o código recebido por tokens
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials
    
    # Salva o refresh_token no banco de dados
    db.save_user_token(whatsapp_id, credentials.refresh_token)
    
    # Avisa o usuário que a conexão foi um sucesso
    message = ("🎉 Autorização concluída com sucesso!\n\n"
               "Agora, por favor, me envie a URL da sua planilha de controle financeiro usando o comando:\n\n"
               "*/configurar <URL_DA_PLANILHA>*")
    meta_client.send_message(number=whatsapp_id, text=message)
    
    return Response(content="<h1>Autenticação realizada com sucesso!</h1><p>Pode fechar esta janela e voltar para o WhatsApp.</p>", media_type="text/html")
