from service.helpers import convert_decimals

def obtener_memoria(table, user_id):
    response = table.get_item(Key={"user_id": user_id})

    memory = response.get("Item", {
        "user_id": user_id,
        "destination": None,
        "people": None,
        "date": None,
        "budget": None,
        "lead_status": "cold",
        "history": [],
        "email": None,
        "country": "No definido",
        "lead_sent": False,
        "lead_id": None,
    
        "conversation_owner": "bot",
        "last_human_interaction": None,
    
        "user_type": None,
        "phone_contact": None,
        "budget_status": None,
        "budget_known": False,
        "name": None,
        "policy": None,
        "bot_disabled_until": None,
    })

    return memory

def sincronizar_memoria(
    memory,
    extracted,
    required_fields,
    optional_fields,
    channel,
    ai_response=None
):

    print("=== SYNC INPUT ===", "extracted:", extracted, "ai_response:", ai_response)
    campos_memoria = required_fields.copy()

    for campo in optional_fields:
        if campo not in campos_memoria:
            campos_memoria.append(campo)

    if "phone_contact" not in campos_memoria:
        campos_memoria.append("phone_contact")

    for key in campos_memoria:
        val = extracted.get(key)
        if val and str(val).lower() not in ["null", "none"]:
            if key == "phone_contact" and channel == "whatsapp":
                continue
            memory[key] = val
    
    # Leer inteligencia del modelo desde ai_response (ahora limpio, no desde extracted)
    if ai_response:
        if ai_response.get("intent"):
            memory["last_intent"] = ai_response["intent"]
        if ai_response.get("confidence"):
            memory["last_confidence"] = ai_response["confidence"]
        if ai_response.get("next_action"):
            memory["last_next_action"] = ai_response["next_action"]
        if ai_response.get("reasoning"):
            memory["last_reasoning"] = ai_response["reasoning"]
    
    # Guardar historial de next_actions para detectar ciclos (opcional pero útil)
        if "next_actions_history" not in memory:
            memory["next_actions_history"] = []
        if memory.get("last_next_action"):
            memory["next_actions_history"].append(memory["last_next_action"])
            memory["next_actions_history"] = memory["next_actions_history"][-10:]

    return memory

def guardar_memoria(
    table,
    memory,
    user_question,
    ai_response,
    new_status
):

    memory["lead_status"] = new_status

    history = memory.get("history", [])

    history.append({
        "user": user_question,
        "assistant": ai_response.get("answer", "")
    })

    memory["history"] = history[-20:]

    table.put_item(
        Item=convert_decimals(memory)
    )