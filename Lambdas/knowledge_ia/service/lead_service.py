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
            (filled == len(required_fields) and memory.get("phone_contact") and policy["require_phone_for_hot"])
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

def obtener_campos_faltantes(memory, prompt_config):
    required_fields = prompt_config.get("required_fields") or prompt_config.get("lead_fields") or []
    
    # NUEVO: Leer contexto conversacional de la memoria
    last_intent = memory.get("last_intent", "proporcionar_dato")
    campos_rechazados = memory.get("campos_rechazados", [])
    
    faltantes = []

    for campo in required_fields:
        # Si ya existe, no es faltante
        if memory.get(campo):
            continue
        
        # NUEVO: Si el usuario consultó disponibilidad de este campo, no lo trates como faltante ahora
        if campo == "date" and last_intent == "consultar_disponibilidad":
            continue
            
        # NUEVO: Si el usuario ya rechazó dar este dato, no lo pidas de nuevo
        if campo in campos_rechazados:
            continue

        faltantes.append(campo)

    return required_fields, faltantes