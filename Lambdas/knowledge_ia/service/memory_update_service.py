from service.helpers import calcular_estado_presupuesto
from service.memory_service import sincronizar_memoria


def actualizar_memoria(
    memory,
    extracted,
    user_question,
    ai_response,
    lead_fields,
    policy,
    channel
):
    
    # 3. Sincronizar Memoria
    memory = sincronizar_memoria(
        memory=memory,
        extracted=extracted,
        lead_fields=lead_fields,
        channel=channel
    )
    
    # Business rules
    if (
        memory.get("destination")
        and memory.get("people")
        and memory.get("date")
        and memory.get("budget_unknown")
        and policy["ask_phone"]
        and not memory.get("phone_contact")
    ):
        ai_response["answer"] = (
            "Entiendo! Si aún no cuentas con un presupuesto definido, "
            "uno de nuestros asesores puede orientarte sobre costos y opciones disponibles. "
            "Por favor indícanos un número de teléfono o un correo electrónico y nos pondremos en contacto contigo lo antes posible."
        )
    
    if (
        memory.get("budget_unknown")
        and memory.get("phone_contact")
    ):
    
        ai_response["answer"] = (
            "Perfecto. Hemos recibido tu número de contacto. "
            "Uno de nuestros asesores se comunicará contigo lo antes posible para ayudarte a evaluar opciones y presupuesto para tu viaje."
        )        
    texto_normalizado = user_question.lower().strip()
    if (
        memory.get("destination")
        and memory.get("people")
        and memory.get("date")
        and not memory.get("budget")
        and texto_normalizado in [
            "no se",
            "no sé",
            "nose",
            "ni idea",
            "desconozco",
            "no lo se",
            "no lo sé"
        ]
    ):
        
        memory["budget_unknown"] = True        
    
    memory["budget_status"] = calcular_estado_presupuesto(
        memory.get("destination"),
        memory.get("people"),
        memory.get("budget")
    )
    print("DESTINO:", memory.get("destination"))
    print("PERSONAS:", memory.get("people"))
    print("PRESUPUESTO:", memory.get("budget"))
    print("BUDGET STATUS:", memory.get("budget_status"))
    print("BUDGET UNKNOWN:", memory.get("budget_unknown"))
    if (
        memory["budget_status"] == "low"
        and memory.get("destination")
        and memory.get("people")
        and memory.get("date")
        and policy["ask_phone"]
        and not memory.get("phone_contact")
    ):
       ai_response["answer"] = (
           "Gracias por compartir los datos de tu viaje. "
           "Para el destino y la cantidad de viajeros indicados, el presupuesto podría resultar ajustado según las fechas y la disponibilidad. "
           "Si lo deseas, déjanos un número de contacto o un correo electrónico y un asesor se comunicará contigo lo antes posible para ayudarte a encontrar mejores opciones."
        )
       
    elif (
        memory["budget_status"] == "low"
        and memory.get("phone_contact")
    ):
        ai_response["answer"] = (
            "Perfecto. Hemos recibido tu número de contacto. "
            "Un asesor se comunicará contigo lo antes posible."
        )
    return memory   