import requests
import time

import time

def responder_whatsapp(
    texto,
    chat_id,
    send_messages,
    instance,
    token
):

    if send_messages and instance and token:

        tiempo_espera = min(
            max(len(texto) / 50, 2),
            5
        )

        print(
            f"Esperando {tiempo_espera} segundos antes de responder por WhatsApp..."
        )

        time.sleep(tiempo_espera)

        enviar_respuesta_whatcrm(
            instance,
            token,
            chat_id,
            texto
        )

    else:

        print("Modo desarrollo: mensaje NO enviado a WhatsApp.")

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