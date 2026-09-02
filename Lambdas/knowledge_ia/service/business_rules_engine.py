from service.helpers import calcular_estado_presupuesto


def aplicar_reglas_negocio(
    memory,
    ai_response,
    policy,
    user_question,
    business_config,
    channel,
):

    rules = business_config.get(
        "business_rules",
        {}
    )

    if rules.get("budget_validation", False):

        memory = aplicar_reglas_presupuesto(
            memory=memory,
            ai_response=ai_response,
            policy=policy,
            user_question=user_question,
            rules=rules,
            channel=channel,
        )

    return memory
    
    
def aplicar_reglas_presupuesto(
    memory,
    ai_response,
    policy,
    user_question,
    rules,
    channel,
):
    
    fields = rules.get(
        "budget_fields",
        {}
    )
    
    destination_field = fields.get(
        "destination",
        "destination"
    )
    
    people_field = fields.get(
        "people",
        "people"
    )
    
    date_field = fields.get(
        "date",
        "date"
    )
    
    budget_field = fields.get(
        "budget",
        "budget"
    )

    puede_pedir_telefono = (
        policy.get("ask_phone", False)
        and channel != "whatsapp"
    )

    # Business rules
    if (
        memory.get(destination_field)
        and memory.get(people_field)
        and memory.get(date_field)
        and memory.get("budget_unknown")
        and puede_pedir_telefono
        and not memory.get("phone_contact")
    ):
        ai_response["answer"] = (
            "Entiendo! Si aún no cuentas con un presupuesto definido, "
            "uno de nuestros asesores puede orientarte sobre costos y opciones disponibles. "
            "Por favor indícanos un número de teléfono o un correo electrónico y nos pondremos en contacto contigo lo antes posible."
        )

        ai_response["next_action"] = "request_phone"
    
    if (
        memory.get("budget_unknown")
        and memory.get("phone_contact")
    ):
    
        ai_response["answer"] = (
            "Perfecto. Hemos recibido tu número de contacto. "
            "Uno de nuestros asesores se comunicará contigo lo antes posible para ayudarte a evaluar opciones y presupuesto para tu viaje."
        )

        ai_response["next_action"] = "delegate_human"

    texto_normalizado = user_question.lower().strip()
    if (
        memory.get(destination_field)
        and memory.get(people_field)
        and memory.get(date_field)
        and not memory.get(budget_field)
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
        memory.get(destination_field),
        memory.get(people_field),
        memory.get(budget_field)
    )
    print("DESTINO:", memory.get(destination_field))
    print("PERSONAS:", memory.get(people_field))
    print("PRESUPUESTO:", memory.get(budget_field))
    print("BUDGET STATUS:", memory.get("budget_status"))
    print("BUDGET UNKNOWN:", memory.get("budget_unknown"))

    if (
        memory["budget_status"] == "low"
        and memory.get(destination_field)
        and memory.get(people_field)
        and memory.get(date_field)
        and puede_pedir_telefono
        and not memory.get("phone_contact")
    ):
       ai_response["answer"] = (
           "Gracias por compartir los datos de tu viaje. "
           "Para el destino y la cantidad de viajeros indicados, el presupuesto podría resultar ajustado según las fechas y la disponibilidad. "
           "Si lo deseas, déjanos un número de contacto o un correo electrónico y un asesor se comunicará contigo lo antes posible para ayudarte a encontrar mejores opciones."
        )

       ai_response["next_action"] = "request_phone"
       
    elif (
        memory["budget_status"] == "low"
        and memory.get("phone_contact")
    ):
        ai_response["answer"] = (
            "Perfecto. Hemos recibido tu número de contacto. "
            "Un asesor se comunicará contigo lo antes posible."
        )

        ai_response["next_action"] = "delegate_human"

    return memory 
