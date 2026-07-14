import boto3
import os

def puede_responder(memory, config, channel):

    # La web siempre responde
    if channel == "web":
        return True

    # Si un asesor tomó esta conversación,
    # el bot no responde más.
    if memory.get("human_agent"):
        return False

    # Si el bot está deshabilitado globalmente.
    if not config.get("bot_enabled", True):
        return False

    return True

def obtener_configuracion(config_table):

    response = config_table.get_item(
        Key={
            "config_id": "global"
        }
    )

    return response.get("Item")

def obtener_o_crear_configuracion(
    config_table,
    business_config
   ):

    config = obtener_configuracion(config_table)

    if config:
        return config

    config = {
        "config_id": "global",
    
        # Estado del bot
        "bot_enabled": True,
        "maintenance_mode": False,
    
        # Administración
        "admin_phone": business_config.get("admin_phone"),

        "business_timezone": business_config.get(
            "timezone",
            "UTC"
        )
    }
    
    print("Configuración global creada.")
    config_table.put_item(Item=config)

    return config

def guardar_configuracion(config_table, config):

    config_table.put_item(
        Item=config
    )


def es_administrador(user_id, config):

    numero = user_id.split("@")[0]

    admin = config.get("admin_phone")

    if admin and numero == admin:
        return True

    return False

def es_comando_admin(texto):
    if not texto:
        return False

    return texto.strip().lower().startswith("#bot")
