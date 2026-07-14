from service.memory_service import obtener_memoria
from service.helpers import detectar_tipo_usuario, detectar_pais


def preparar_contexto_usuario(
    table,
    user_id,
    user_question
):

    memory = obtener_memoria(
        table,
        user_id
    )

    nuevo_tipo = detectar_tipo_usuario(user_question)

    if nuevo_tipo != "lead":
        memory["user_type"] = nuevo_tipo

    elif not memory.get("user_type"):
        memory["user_type"] = "lead"

    pais_det = detectar_pais(user_question)

    if pais_det != "No definido":
        memory["country"] = pais_det

    return memory