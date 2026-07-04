import boto3

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

def obtener_o_crear_configuracion(config_table):

    config = obtener_configuracion(config_table)

    if config:
        return config

    config = {
        "config_id": "global",
    
        # Estado del bot
        "bot_enabled": True,
        "maintenance_mode": False,
    
        # Horarios
        "working_hours_enabled": False,
        "working_start": "09:00",
        "working_end": "18:00",
        "timezone": "America/Argentina/Buenos_Aires",
    
        # Administración
        "admin_phone": None
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

    return numero == config.get("admin_phone")

def es_comando_admin(texto):
    if not texto:
        return False

    return texto.strip().lower().startswith("#bot")
