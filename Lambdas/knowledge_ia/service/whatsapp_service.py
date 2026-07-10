import requests
import time
import json

import time
from service.config_service import (
    guardar_configuracion
)

from service.business_service import (
    guardar_business_config
)

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

def procesar_comando_admin(
    comando,
    user_id,
    config,
    config_table,
    business_config,
    send_messages,
    instance,
    token,
    bucket_name,
    business_file
):
        
    comando = comando.strip().lower()

    if comando == "#bot status":

        estado = (
            "ACTIVO ✅"
            if config.get("bot_enabled", True)
            else "DESACTIVADO ⛔"
        )
    
        admin = config.get("admin_phone") or "No registrado"
    
        respuesta = (
            f"🤖 Estado: {estado}\n"
        )
    
        responder_whatsapp(
            respuesta,
            user_id,
            send_messages,
            instance,
            token
        )
    
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": respuesta
            })
        }

    elif comando == "#bot off":

        config["bot_enabled"] = False
        guardar_configuracion(config_table, config)
    
        respuesta = "🤖 Bot DESACTIVADO ⛔"
    
        responder_whatsapp(
            respuesta,
            user_id,
            send_messages,
            instance,
            token
        )
    
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": respuesta
            })
        }
    
    
    elif comando == "#bot on":
    
        config["bot_enabled"] = True
        guardar_configuracion(config_table, config)
    
        respuesta = "🤖 Bot ACTIVADO ✅"
    
        responder_whatsapp(
            respuesta,
            user_id,
            send_messages,
            instance,
            token
        )
    
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": respuesta
            })
        }
    
    
    elif comando == "#bot help":
    
        respuesta = (
            "🤖 Comandos disponibles\n\n"
            "• #bot on\n"
            "• #bot off\n"
            "• #bot status\n"
            "• #bot help\n"
            "• #bot config\n"
            "• #bot stats\n"
            "• #bot horario\n"
            "• #bot reload"
        )
    
        responder_whatsapp(
            respuesta,
            user_id,
            send_messages,
            instance,
            token
        )
    
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": respuesta
            })
        }

    elif comando == "#bot horario":

        business = business_config
        horario = business.get("working_hours", {})
    
        dias = [
            ("monday", "Lunes"),
            ("tuesday", "Martes"),
            ("wednesday", "Miércoles"),
            ("thursday", "Jueves"),
            ("friday", "Viernes"),
            ("saturday", "Sábado"),
            ("sunday", "Domingo")
        ]
    
        estado = (
            "🟢 Activado"
            if horario.get("enabled", False)
            else "🔴 Desactivado"
        )
    
        respuesta = (
            "🕒 Horario configurado\n\n"
            f"Estado: {estado}\n"
            f"🌍 Zona horaria: {business.get('timezone', 'UTC')}\n\n"
        )
    
        for clave, nombre in dias:

            h = horario.get(clave)
        
            if h is None:
                respuesta += f"{nombre}: Cerrado\n"
            else:
                respuesta += (
                    f"{nombre}: "
                    f"{h['start']} - {h['end']}\n"
                )
    
        responder_whatsapp(
            respuesta,
            user_id,
            send_messages,
            instance,
            token
        )
    
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": respuesta
            })
        }

    elif comando == "#bot horario on":

        business_config["working_hours"]["enabled"] = True
    
        guardar_business_config(
            bucket_name,
            business_file,
            business_config
        )
    
        respuesta = "🕒 Control de horario ACTIVADO ✅"
    
        responder_whatsapp(
            respuesta,
            user_id,
            send_messages,
            instance,
            token
        )
    
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": respuesta
            })
        }

    elif comando == "#bot horario off":

        business_config["working_hours"]["enabled"] = False
    
        guardar_business_config(
            bucket_name,
            business_file,
            business_config
        )
    
        respuesta = "🕒 Control de horario DESACTIVADO ⛔"
    
        responder_whatsapp(
            respuesta,
            user_id,
            send_messages,
            instance,
            token
        )
    
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": respuesta
            })
        } 
    

