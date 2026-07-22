from service.bot_pause_service import (
    bot_esta_pausado,
    pausar_bot,
    activar_bot
)

from datetime import datetime

def puede_responder(memory, config, channel):

    # La web siempre responde
    if channel == "web":
        return True

    # ============================
    # Chat pausado temporalmente
    # ============================

    bot_disabled_until = memory.get("bot_disabled_until")

    if bot_disabled_until:

        try:

            fecha = datetime.fromisoformat(bot_disabled_until)

            if datetime.utcnow() < fecha:
                return False

            # Si ya venció, el bot vuelve a responder normalmente.
            memory["bot_disabled_until"] = None

        except Exception:
            memory["bot_disabled_until"] = None

    # ============================
    # Bot global
    # ============================

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