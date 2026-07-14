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
        "human_agent": False,
        "user_type": None,
        "phone_contact": None,
        "budget_status": None,
        "budget_known": False,
        "name": None,
        "policy": None
    })

    return memory

def actualizar_campos_basicos(memory, ai_response):

    campos = [
        "destination",
        "people",
        "date",
        "budget",
        "email",
        "name",
        "country"
    ]

    for campo in campos:

        valor = ai_response.get(campo)

        if valor not in [None, "", "No definido"]:

            memory[campo] = valor

    return memory

def sincronizar_memoria(
    memory,
    extracted,
    lead_fields,
    channel
):

    campos_memoria = lead_fields.copy()

    if "phone_contact" not in campos_memoria:
        campos_memoria.append("phone_contact")

    for key in campos_memoria:

        val = extracted.get(key)

        if val and str(val).lower() not in ["null", "none"]:

            if key == "phone_contact" and channel == "whatsapp":
                continue

            memory[key] = val

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