#CONSTRUYE EL PROMPT
import json

from service.helpers import (
    convert_decimals,
    normalizar_extracciones
)

from service.prompt_builder_service import (
    construir_datos_obtenidos,
    construir_datos_faltantes,
    construir_json_extraccion,
    construir_system_prompt,
)

def obtener_respuesta_ai(
    client,
    prompt_config,
    agency_knowledge,
    memory,
    user_question,
    faltantes_texto,
    required_fields,
    channel,
):
    
    safe_memory = convert_decimals(memory)
    datos_obtenidos = construir_datos_obtenidos(
        memory,
        required_fields
    )

    datos_faltantes = construir_datos_faltantes(
        faltantes_texto.split(", ") if faltantes_texto else []
    )
    
    json_extraccion = construir_json_extraccion(
        prompt_config,
        required_fields
    )
    
    system_prompt = construir_system_prompt(
        prompt_config=prompt_config,
        agency_knowledge=agency_knowledge,
        safe_memory=json.dumps(safe_memory),
        datos_obtenidos=datos_obtenidos,
        datos_faltantes=datos_faltantes,
        memory=memory,
        json_extraccion=json_extraccion,
        channel=channel,
    )

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
    extracted = normalizar_extracciones(extracted, user_question)
    
    # NUEVO: Leer la inteligencia conversacional que devolvió el modelo
    intent = ai_response.get("intent", "proporcionar_dato")
    confidence = ai_response.get("confidence", "high")
    next_action = ai_response.get("next_action", "continue_collecting")
    reasoning = ai_response.get("reasoning", "")

    print(f"========== INTELLIGENCE ==========")
    print(f"intent: {intent} | confidence: {confidence} | next_action: {next_action}")
    print(f"reasoning: {reasoning}")

    # =====================================================
    # REGLA DE CANAL
    # =====================================================
    
    if channel == "whatsapp" and next_action == "request_phone":
    
        print(
            "=== CHANNEL OVERRIDE: WhatsApp no permite request_phone ===",
            flush=True
        )
    
        next_action = "derivar_humano"
    
        reasoning = (
            "La acción request_phone no está permitida en WhatsApp. "
            "La conversación debe continuar mediante derivación humana "
            "sin solicitar un teléfono adicional."
        )
    
        ai_response["next_action"] = next_action
        ai_response["reasoning"] = reasoning

    # =====================================================
    # VALIDACIÓN DE HANDOFF
    # =====================================================
    
    if next_action == "derivar_humano":
    
        print(
            "=== HANDOFF DETECTADO ===",
            flush=True
        )
    
        print(
            f"HANDOFF ANSWER: {ai_response.get('answer', '')}",
            flush=True
        )
    
    # =====================================================
    # INTELIGENCIA FINAL
    # =====================================================
    
    ai_response["intent"] = intent
    ai_response["confidence"] = confidence
    ai_response["next_action"] = next_action
    ai_response["reasoning"] = reasoning
    
    print(
        f"========== FINAL INTELLIGENCE ==========",
        flush=True
    )
    
    print(
        f"intent: {intent} | "
        f"confidence: {confidence} | "
        f"next_action: {next_action}",
        flush=True
    )
    
    print(
        f"reasoning: {reasoning}",
        flush=True
    )
    
    return ai_response