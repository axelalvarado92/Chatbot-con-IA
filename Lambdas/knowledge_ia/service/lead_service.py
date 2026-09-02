def calcular_estado_lead(
    memory,
    required_fields,
    policy
):
    
    filled = sum(
        1
        for k in required_fields
        if memory.get(k)
    )

    base_complete = (
        filled == len(required_fields)
    )

    budget_status = memory.get("budget_status")

    base_complete = all(
        memory.get(field)
        for field in required_fields
    )


    if policy["auto_hot"]:
        new_status = "hot" if base_complete else "warm"
    else:
        if (
            (filled == len(required_fields) and memory.get("phone_contact") and policy["require_phone_for_hot"])
            or
            (base_complete and memory.get("budget_unknown") and memory.get("phone_contact") and policy["require_phone_for_hot"])
            or
            (base_complete and not policy["require_phone_for_hot"])
        ):
            new_status = "hot"
        elif base_complete:
            new_status = "warm"
        else:
            new_status = "cold"

    return new_status

def obtener_campos_faltantes(memory, required_fields):

    # =====================================================
    # CONTEXTO CONVERSACIONAL
    # =====================================================

    last_intent = memory.get(
        "last_intent",
        "proporcionar_dato"
    )

    campos_rechazados = memory.get(
        "campos_rechazados",
        []
    )

    faltantes = []

    for campo in required_fields:

        # Si ya existe, no es faltante
        if memory.get(campo):
            continue

        # Si el usuario consultó disponibilidad de este campo,
        # no lo trates como faltante inmediatamente
        if (
            campo == "date"
            and last_intent == "consultar_disponibilidad"
        ):
            continue

        # Si el usuario rechazó proporcionar este dato,
        # no lo vuelvas a solicitar automáticamente
        if campo in campos_rechazados:
            continue

        faltantes.append(campo)

    return required_fields, faltantes