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

    ignorar = {
        "assistant_name",
        "company_name",
        "assistant_role"
    }

    for clave, valor in prompt_config.items():

        if clave in ignorar:
            continue

        if isinstance(valor, list):

            titulo = clave.replace("_", " ").upper()

            contenido = "\n".join(valor)

            secciones.append(
                f"{titulo}:\n{contenido}"
            )

    return "\n\n".join(secciones)

def construir_system_prompt(
    prompt_config,
    agency_knowledge,
    safe_memory,
    datos_obtenidos,
    datos_faltantes,
    memory,
    json_extraccion
):

    secciones_prompt = construir_secciones_prompt(
        prompt_config
    )

    return f"""
CONOCIMIENTO DEL NEGOCIO:
{agency_knowledge}

{prompt_config["assistant_role"]}

MEMORIA CLIENTE:
{safe_memory}

DATOS YA OBTENIDOS:
{datos_obtenidos}

DATOS FALTANTES:
{datos_faltantes}

ESTADO PRESUPUESTO:
{memory.get("budget_status")}

{secciones_prompt}

RESPONDE SIEMPRE EN JSON:
{json_extraccion}

"""

def construir_json_extraccion(required_fields):

    extracted = {
        campo: None
        for campo in required_fields
    }

    return json.dumps(
        {
            "answer": "tu respuesta",
            "extracted_data": extracted
        },
        indent=2,
        ensure_ascii=False
    )