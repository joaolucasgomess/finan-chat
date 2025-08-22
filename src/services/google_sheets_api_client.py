import locale
import os
import gspread
from dotenv import load_dotenv
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from src.utils.convert_to_brl import parse_brl


locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")

load_dotenv()

class GoogleSheetsAPIClient:
    CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE')
    SCOPES = [os.getenv('SCOPE_SHEETS'), os.getenv('SCOPE_DRIVE')]

    def __get_credentials_for_user(self, refresh_token: str):
        creds = Credentials.from_authorized_user_info(
            info={'refresh_token': refresh_token, 
                  'client_id': os.getenv('GOOGLE_CLIENT_ID'), 
                  'client_secret': os.getenv('GOOGLE_CLIENT_SECRET')
            },
            scopes=self.SCOPES
        )

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    
    def update_sheet(self, refresh_token: str, spreadsheet_id: str, type: str, value: float, date: datetime, date_now: datetime):
        if not refresh_token or not spreadsheet_id:
            raise ValueError("Credenciais ou ID da planilha não fornecidos.")
        
        user_credentials = self.__get_credentials_for_user(refresh_token)
        client = gspread.authorize(user_credentials)
        
        worksheet = client.open_by_key(key=spreadsheet_id).worksheet(title=str(date.year))

        month_name = date.strftime('%B').upper()
        month = worksheet.find(in_row=1, case_sensitive=True, query=month_name)
        if not month:
            return f"Não encontrei o mês de {month_name} na sua planilha."
        
        day = worksheet.find(in_column=month.col, query=str(date.day))
        if not day:
            return f"Não encontrei o dia {date.day} na coluna do mês de {month_name}."
        
        col_map = {'Entrada': 1, 'Saida': 2, 'Diario': 3}
        col_to_update = month.col + col_map.get(type)

        if col_to_update:
            worksheet.update_cell(row=day.row, col=col_to_update, value=f'={value}')

            month_balance = worksheet.col_values(col=(month.col + 4))
            month_balance_converted = [parse_brl(v) for v in month_balance[2:] if v.strip()]

            balance_today = month_balance_converted[date_now.day - 1]            

            if balance_today < 0:
                return f'Lançamento de {type.lower()} (R$ {value}) feito com sucesso em {date.strftime("%d/%m/%Y")}\n\nSaldo de hoje: R$ {balance_today}\n\nSaldo ultimo dia do mes: {month_balance_converted[-1]}'

            negative = next(((i, v) for i, v in enumerate(month_balance_converted) if v < 0), None)

            if negative:
                index, negative_value = negative
                return f'Lançamento de {type.lower()} (R$ {value}) feito com sucesso em {date.strftime("%d/%m/%Y")}\n\nSaldo de hoje: R$ {balance_today}\n\nProximo saldo negativo este mes: R$ {negative_value} no dia {(index + 1)}\n\nSaldo ultimo dia do mes: {month_balance_converted[-1]}'
                
            return f'Lançamento de {type.lower()} (R$ {value}) feito com sucesso em {date.strftime("%d/%m/%Y")}\n\nSaldo de hoje: R$ {balance_today}\n\nSaldo ultimo dia do mes: {month_balance_converted[-1]}'
        
        return "Tipo de lançamento inválido."
