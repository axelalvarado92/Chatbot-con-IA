def calcular_estado_lead(
    memory,
    lead_fields,
    channel,
    policy
):
    
    filled = sum(
        1
        for k in lead_fields
        if memory.get(k)
    )
    budget_status = memory.get("budget_status")
    base_hot = (
        memory.get("destination")
        and memory.get("people")
        and memory.get("date")
    )
    if policy["auto_hot"]:
        new_status = "hot" if base_hot else "warm"
    else:
        if (
            (filled == len(lead_fields) and memory.get("phone_contact") and policy["require_phone_for_hot"])
            or
            (base_hot and memory.get("budget_unknown") and memory.get("phone_contact") and policy["require_phone_for_hot"])
            or
            (base_hot and not policy["require_phone_for_hot"])
        ):
            new_status = "hot"
        elif base_hot:
            new_status = "warm"
        else:
            new_status = "cold"

    return new_status

def obtener_campos_faltantes(
    memory,
    prompt_config
):
    lead_fields = prompt_config.get(
        "lead_fields",
        ["destination", "people", "date", "budget"]
    )

    faltantes = []

    for campo in lead_fields:
        if not memory.get(campo):
            faltantes.append(campo)

    return lead_fields, faltantes