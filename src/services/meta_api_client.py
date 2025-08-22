# services/meta_api_client.py
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class MetaAPIClient:
    API_VERSION = "v23.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
    
    def __init__(self):
        self.__access_token = os.getenv('META_ACCESS_TOKEN')
        self.__phone_number_id = os.getenv('META_PHONE_NUMBER_ID')
        self.__headers = {
            "Authorization": f"Bearer {self.__access_token}",
            "Content-Type": "application/json"
        }
        self.__url = f"{self.BASE_URL}/{self.__phone_number_id}/messages"

    def send_message(self, number: str, text: str):
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "text",
            "text": {
                "body": text
            }
        }

        print("---------------------------------")
        print(f"Enviando para a API do Graph:")
        print(f"URL: {self.__url}")
        print(f"Headers: {self.__headers}")
        print(f"Payload: {json.dumps(payload, indent=2)}") # Usamos json.dumps para formatar bem
        print("---------------------------------")
        

        try:
            response = requests.post(self.__url, json=payload, headers=self.__headers)
            response.raise_for_status()  # Lança um erro para respostas 4xx ou 5xx
            print(f"Mensagem enviada para {number}: {response.json()}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"!!! Erro ao enviar mensagem para {number}: {e}")
            if e.response is not None:
                print(f"!!! Status Code: {e.response.status_code}")
                print(f"!!! Resposta da Meta: {e.response.text}") 
            return None