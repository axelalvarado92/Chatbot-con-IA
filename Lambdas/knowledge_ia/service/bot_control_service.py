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