from service.memory_service import obtener_memoria
from service.helpers import detectar_tipo_usuario, detectar_pais

def detectar_rechazos(user_question, memory):
    texto = user_question.lower().strip()
    
    if "campos_rechazados" not in memory:
        memory["campos_rechazados"] = []
    # 1. Rechazo explícito de fecha (más flexible)
    if any(p in texto for p in ["no tengo fecha", "no sé la fecha", "no se la fecha", 
                                  "no tengo una fecha", "sin fecha", "no se cuando", 
                                  "no sé cuando", "no tengo idea de fecha"]):
        if "date" not in memory.get("campos_rechazados", []):
            memory.setdefault("campos_rechazados", []).append("date")
    
    # 2: Rechazo implícito por contexto
    ultima_intent = memory.get("last_intent")
    ultima_action = memory.get("last_next_action")
    
    if ultima_intent in ["consultar_disponibilidad", "ask_date"] and \
       any(p in texto for p in ["no tengo", "no se", "no sé", "todavía no", "todavia no", "no por ahora"]):
        if "date" not in memory.get("campos_rechazados", []):
            memory.setdefault("campos_rechazados", []).append("date")
    
    if any(p in texto for p in ["no tengo presupuesto", "no sé cuánto", "no se cuanto", "sin presupuesto"]):
        if "budget" not in memory["campos_rechazados"]:
            memory["campos_rechazados"].append("budget")
    
    if any(p in texto for p in ["no sé cuántos", "no se cuantos", "todavía no sé", "todavia no se", "solo yo por ahora"]):
        if "people" not in memory["campos_rechazados"]:
            memory["campos_rechazados"].append("people")
    
    return memory


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

    memory = detectar_rechazos(user_question, memory)

    return memory