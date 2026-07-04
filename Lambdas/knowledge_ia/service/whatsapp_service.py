import requests

def enviar_respuesta_whatcrm(WHATCRM_INSTANCE, WHATCRM_TOKEN, chat_id, texto):

    url = f"https://api.whatcrm.net/instances/{WHATCRM_INSTANCE}/sendMessage"
    
    headers = {
        "X-Crm-Token": WHATCRM_TOKEN,
        "Content-Type": "application/json"
    }
    
    payload = {
        "chatId": chat_id,
        "body": texto,
        "sendSeen": "1"
    }
    
    res = requests.post(url, json=payload, headers=headers, timeout=10)
    print(f"URL utilizada: {url}")
    print(f"WhatCRM response: {res.status_code} - {res.text}")