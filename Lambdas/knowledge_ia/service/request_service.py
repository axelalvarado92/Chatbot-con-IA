import json

from service.bot_control_service import es_comando_admin


def parse_request(body, business_config):

    if "question" in body:
        request = _parse_web(body, business_config)

    elif "messages" in body:
        request = _parse_whatsapp(body, business_config)

    else:
        raise Exception("Formato de request no soportado")

    if request is None:
        return None

    if not request["user_id"] or not request["question"]:
        raise Exception("Faltan datos")

    return request

def _parse_web(body, business_config):

    return {

        "channel": "web",

        "policy": business_config["channels"]["web"],

        "user_id": body.get("user_id"),

        "chat_id": body.get("user_id"),

        "question": body.get("question"),

        "is_admin_command": False
    }

def _parse_whatsapp(body, business_config):

    messages = body.get("messages", [])

    if len(messages) == 0:
        raise Exception("No hay mensajes")

    mensaje = messages[0]

    es_admin = es_comando_admin(
        mensaje.get("body", "")
    )

    if mensaje.get("fromMe") and not es_admin:
        return None

    chat_id = mensaje.get("chatId")

    if es_admin:
        user_id = mensaje.get("from")
    else:
        user_id = chat_id

    return {

        "channel": "whatsapp",

        "policy": business_config["channels"]["whatsapp"],

        "user_id": user_id,

        "chat_id": chat_id,

        "question": mensaje.get("body"),

        "is_admin_command": es_admin
    }