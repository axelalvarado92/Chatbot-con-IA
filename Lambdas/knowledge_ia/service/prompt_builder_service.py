import json

def construir_datos_obtenidos(memory, required_fields):

    lineas = []

    for campo in required_fields:

        valor = memory.get(campo)

        if valor:
            lineas.append(f"{campo}: {valor}")

    if not lineas:
        return "Ningún dato obtenido todavía."

    return "\n".join(lineas)

def construir_datos_faltantes(faltantes):

    if not faltantes:
        return "No faltan datos."

    return "\n".join(f"- {campo}" for campo in faltantes)

def construir_secciones_prompt(prompt_config):
    secciones = []
    
    for clave, valor in prompt_config.items():
        # Solo procesar listas de strings puros
        if not isinstance(valor, list):
            continue
        if not all(isinstance(v, str) for v in valor):
            continue
        
        titulo = clave.replace("_", " ").upper()
        contenido = "\n".join(valor)
        secciones.append(f"{titulo}:\n{contenido}\n")
    
    return "\n".join(secciones)

def construir_system_prompt(
    prompt_config,
    agency_knowledge,
    safe_memory,
    datos_obtenidos,
    datos_faltantes,
    memory,
    json_extraccion,
    channel,
):

    # 1. Armar textos de intenciones y acciones
    intents = prompt_config.get("intents", {})
    next_actions = prompt_config.get("next_actions", {})
    intent_behavior = prompt_config.get("intent_behavior", {})
    handoff_rules = prompt_config.get("handoff_rules",[])
    
    intents_text = "\n".join([f'- {k}: {v}' for k, v in intents.items()])
    next_actions_text = "\n".join([f'- {k}: {v}' for k, v in next_actions.items()])
    intent_behavior_text = "\n".join([f"- {k}: {v}" for k, v in intent_behavior.items()])
    handoff_rules_text = "\n".join(f"- {rule}"for rule in handoff_rules)
    

    # 2. Armar ejemplos para el prompt
    ejemplos_raw = prompt_config.get("examples", [])
    ejemplos_texto = ""
    
    if ejemplos_raw:
        lineas = ["EJEMPLOS DE RESPUESTAS ESPERADAS:"]
        for i, ex in enumerate(ejemplos_raw, 1):
            resp = ex.get("response", {})
            lineas.append(f"\nEjemplo {i}:")
            lineas.append(f'  Usuario: "{ex.get("user", "")}"')
            lineas.append(f'  → Respuesta: "{resp.get("answer", "")}"')
            lineas.append(f'  → Intent: {resp.get("intent", "")}')
            lineas.append(f'  → Next_action: {resp.get("next_action", "")}')
            lineas.append(f'  → Extracted_data: {json.dumps(resp.get("extracted_data", {}), ensure_ascii=False)}')
        ejemplos_texto = "\n".join(lineas) + "\n\n"

    # 3. Armar el resto de secciones
    secciones_prompt = construir_secciones_prompt(prompt_config)

    return f"""
CONOCIMIENTO DEL NEGOCIO:
{agency_knowledge}

{prompt_config["assistant_role"]}

MEMORIA CLIENTE:
{safe_memory}

DATOS YA OBTENIDOS:
{datos_obtenidos}

INFORMACIÓN QUE AÚN NO TENEMOS (contexto de referencia):
{datos_faltantes}

ESTADO PRESUPUESTO:
{memory.get("budget_status")}

CANAL ACTUAL:
{channel}

INTENCIONES POSIBLES DEL USUARIO:
{intents_text}

COMPORTAMIENTO SEGÚN INTENCIÓN:
{intent_behavior_text}

ACCIONES POSIBLES PARA TU SIGUIENTE PASO:
{next_actions_text}

REGLAS DE DERIVACIÓN HUMANA:
{handoff_rules_text}

INSTRUCCIÓN CRÍTICA:
Antes de responder, clasificá la intención del último mensaje del usuario.
Elegí la acción que debe seguir tu respuesta. 
Si el usuario está consultando (no proporcionando datos), tu acción debe ser INFORMATIVA, no extractiva.
Si el usuario rechazó dar un dato, no insistas con el mismo tema.
Nunca pidas un dato que ya figure en "DATOS YA OBTENIDOS".

REGLA DE CANAL:
El canal actual es: {channel}

Si el canal es WhatsApp:
- Si el CANAL ACTUAL es whatsapp, nunca elijas request_phone.
- Si la conversación requiere intervención humana, seleccioná derivar_humano.
- En WhatsApp el chat_id ya identifica la conversación y el asesor puede continuar desde el CRM.

{secciones_prompt}

{ejemplos_texto}
RESPONDE SIEMPRE EN JSON:
{json_extraccion}
"""

def construir_json_extraccion(
    prompt_config,
    required_fields,
    optional_fields
):
    
    # Schema de extracted_data con los campos que ya tenías
    extracted = {
        campo: None
        for campo in required_fields
    }

    # Agregar campos opcionales
    for campo in optional_fields:
        if campo not in extracted:
            extracted[campo] = None
    

    # Leer las opciones válidas desde la config
    intents = list(prompt_config.get("intents", {}).keys())
    next_actions = list(prompt_config.get("next_actions", {}).keys())
    
    intents_str = " | ".join(intents) if intents else "proporcionar_dato | consultar | rechazar"
    next_actions_str = " | ".join(next_actions) if next_actions else "continue_collecting | ask_destination"

    # JSON de ejemplo que va al prompt
    schema = {
        "answer": "tu respuesta conversacional para el usuario",
        "extracted_data": extracted,
        "intent": f"una de: {intents_str}",
        "confidence": "high | low",
        "next_action": f"una de: {next_actions_str}",
        "reasoning": "breve explicación de por qué elegiste esta intención y acción"
    }

    return json.dumps(schema, indent=2, ensure_ascii=False)