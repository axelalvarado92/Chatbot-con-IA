import json

from service.helpers import (
    convert_decimals,
    normalizar_extracciones
)

def obtener_respuesta_ai(
    client,
    prompt_config,
    agency_knowledge,
    memory,
    user_question,
    faltantes_texto,
):
    
    safe_memory = convert_decimals(memory)
    
    system_prompt = f"""
CONTEXTO AGENCIA: {agency_knowledge}
Eres {prompt_config['assistant_name']},
asesora de viajes de {prompt_config['company_name']}.

MEMORIA CLIENTE:
{json.dumps(safe_memory)}

DATOS YA OBTENIDOS:
Destino: {memory.get("destination")}
Viajeros: {memory.get("people")}
Fecha: {memory.get("date")}
Presupuesto: {memory.get("budget")}

DATOS FALTANTES:
{faltantes_texto}

ESTADO PRESUPUESTO:
{memory.get("budget_status")}

TU MISIÓN:
{chr(10).join(prompt_config['mission'])}

REGLAS DE RECOMENDACIÓN:
{chr(10).join(prompt_config['recommendation_rules'])}

REGLAS DE EXTRACCIÓN DE DATOS:
{chr(10).join(prompt_config['extraction_rules'])}

REGLAS DE ORO:
{chr(10).join(prompt_config['golden_rules'])}

LÓGICA DE CIERRE:
{chr(10).join(prompt_config['closing_logic'])}

RESPONDE SIEMPRE EN JSON:
{{
  "answer": "tu respuesta",
  "extracted_data": {{
    "destination": "valor o null",
    "people": "valor o null",
    "date": "valor o null",
    "budget": "valor o null",
    "phone_contact": "valor o null"
  }}
}}
"""

    messages_to_send = [{"role": "system", "content": system_prompt}]

    for msg in memory.get("history", [])[-6:]:

        if msg.get("user"):
            messages_to_send.append({
                "role": "user",
                "content": msg["user"]
            })
        
        if msg.get("assistant"):
            messages_to_send.append({
                "role": "assistant",
                "content": msg["assistant"]
            })

    messages_to_send.append({"role": "user", "content": user_question})

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages_to_send,
        response_format={"type": "json_object"}
    )

    ai_response = json.loads(completion.choices[0].message.content)
    print("========== RAW OPENAI ==========")
    print(completion.choices[0].message.content)
    
    print("========== PARSED ==========")
    print(ai_response)
    
    extracted = ai_response.get("extracted_data", {})

    extracted = normalizar_extracciones(
        extracted,
        user_question
    )
    
    return ai_response