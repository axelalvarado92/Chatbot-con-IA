from datetime import datetime, timedelta


def tomar_conversacion(memory):
    memory["conversation_owner"] = "human"
    memory = tomar_conversacion(memory)
    memory["last_human_interaction"] = datetime.utcnow().isoformat()

    return memory


def liberar_conversacion(memory):
    memory["conversation_owner"] = "bot"
    memory = liberar_conversacion(memory)
    memory["last_human_interaction"] = None

    return memory


def verificar_timeout_conversacion(
    memory,
    business_config
):

    if memory.get("conversation_owner") != "human":
        return memory

    ultimo = memory.get("last_human_interaction")

    if not ultimo:
        return memory

    dias_timeout = (
        business_config
        .get("chat", {})
        .get("human_timeout_days", 15)
    )

    ultima = datetime.fromisoformat(ultimo)

    if datetime.utcnow() - ultima > timedelta(days=dias_timeout):

        memory = liberar_conversacion(memory)

    return memory