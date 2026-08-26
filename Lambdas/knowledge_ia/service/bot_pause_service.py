from datetime import datetime, timedelta

DEFAULT_PAUSE_DAYS = 30


def pausar_bot(memory, dias=DEFAULT_PAUSE_DAYS):

    memory["bot_disabled_until"] = (
        datetime.utcnow() + timedelta(days=dias)
    ).isoformat()

    return memory


def activar_bot(memory):

    memory["bot_disabled_until"] = None

    return memory


def bot_esta_pausado(memory):

    pausa = memory.get("bot_disabled_until")

    if not pausa:
        return False

    try:

        fecha = datetime.fromisoformat(pausa)

        if datetime.utcnow() >= fecha:

            activar_bot(memory)

            return False

        return True

    except Exception:

        activar_bot(memory)

        return False