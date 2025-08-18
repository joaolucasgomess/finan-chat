import re
import os
import dateparser
import locale
from fastapi import FastAPI, Request, Response
from .services.evolution_api_client import EvolutionAPIClient
from .services.google_sheets_api_client import GoogleSheetsAPIClient
from google_auth_oauthlib.flow import Flow
from src.data import db


locale.setlocale(category=locale.LC_TIME, locale='pt_BR.utf8')

sheets_client = GoogleSheetsAPIClient()
evo_client = EvolutionAPIClient()

app = FastAPI()

REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
flow = Flow.from_client_secrets_file(
    sheets_client.CLIENT_SECRET_FILE,
    scopes=sheets_client.SCOPES,
    redirect_uri=REDIRECT_URI
)

@app.post('/message')
async def process_message(request: Request):
    payload = await request.json()

    number_sender = payload['data']['key']['remoteJid'].split("@")[0]
    text = payload['data']['message']['conversation']

    user = db.get_user(number_sender)

    if not user:
        authorization_url, state = flow.authorization_url(access_type='offline', prompt='consent', state=number_sender)

        message = (f"Olá! Para começar, preciso de permissão para acessar suas planilhas.\n\n"
                   f"Clique no link abaixo para autorizar:\n\n{authorization_url}")
        evo_client.send_message(number=number_sender, text=message)

        return {'status': 'auth_started'}
    
    if user and text.lower().startswith('/configurar'):
        try:
            url = text.split(' ')[1]
            # Extrai o ID da URL da planilha
            spreadsheet_id = re.search(r'/d/([a-zA-Z0-9-_]+)', url).group(1)
            db.save_spreadsheet_id(number_sender, spreadsheet_id)
            evo_client.send_message(number=number_sender, text="✅ Planilha configurada com sucesso! Agora você já pode fazer seus lançamentos.")
        except (IndexError, AttributeError):
            evo_client.send_message(number=number_sender, text="Formato inválido. Use: */configurar <URL_DA_SUA_PLANILHA>*")
        return {'status': 'configured'}

    pattern = r'^(Entrada|Saida|Diario)\s+([\d,.]+)\s+(.+)$'
    m = re.match(pattern, text)

    if not m:
        response_message = "Formato inválido. Use: *Tipo Valor Data* (ex: Saida 25,50 hoje)"
        evo_client.send_message(number=number_sender, text=response_message)
        return {'status': 'invalid_format'}
    
    type, value, date = m.groups()

    date_in_datetime = dateparser.parse(date, languages=['pt'])
    if not date_in_datetime:
        response_message = 'Não consegui entender a data. Ex: "hoje" ou "amanha" ou "31/12/2025"'
        evo_client.send_message(number=number_sender, text=response_message)
        return {'message': 'data inválida'}
    
    try:
        response_message = sheets_client.update_sheet(
            refresh_token=user['refresh_token'],
            spreadsheet_id=user['spreadsheet_id'],
            type=type.capitalize(),
            value=value,
            date=date_in_datetime
        )
    except Exception as e:
        print(f"Erro ao atualizar planilha: {e}")
        response_message = "Ocorreu um erro ao tentar atualizar sua planilha. Verifique se ela foi compartilhada corretamente ou se o formato está correto."

    response_message =  sheets_client.update_sheet(type=type, value=value, date=date_in_datetime)

    response = evo_client.send_message(number=number_sender, text=response_message)

    return {'status': 'ok'}

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
    evo_client.send_message(number=whatsapp_id, text=message)
    
    return Response(content="<h1>Autenticação realizada com sucesso!</h1><p>Pode fechar esta janela e voltar para o WhatsApp.</p>", media_type="text/html")
