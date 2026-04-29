import json
import boto3
import os
import requests
import re
from openai import OpenAI
from decimal import Decimal

# --- UTILIDADES ---
def formatear_historial(history):
    if not history: return "No hay historial previo."
    texto = "--- CONVERSACIÓN CON IA MARÍA ---\n"
    for msg in history:
        u = msg.get('user', 'Usuario')
        a = msg.get('assistant', 'María')
        texto += f"Cliente: {u}\nAsistente: {a}\n----------------\n"
    return texto

def convert_decimals(obj):
    if isinstance(obj, list): return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict): return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal): return int(obj) if obj % 1 == 0 else float(obj)
    return obj

def detectar_pais(texto):
    t = texto.lower()
    if any(p in t for p in ["argentina", "argentino", "arg"]): return "Argentina"
    if any(p in t for p in ["españa", "español", "espania", "espańa"]): return "España"
    return "No definido"

# --- CLIENTES ---
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def lambda_handler(event, context):
    try:
        # 0. Configuración Inicial
        TABLE_NAME = os.environ.get("TABLE_NAME")
        BUCKET_NAME = os.environ.get("BUCKET_NAME")
        KNOWLEDGE_FILE = os.environ.get("KNOWLEDGE_FILE")
        BITRIX_WEBHOOK = os.environ.get("BITRIX_WEBHOOK_URL")

        body = json.loads(event.get("body", "{}"))
        user_id = body.get("user_id")
        user_question = body.get("question")

        if not user_id or not user_question:
            return {"statusCode": 400, "body": json.dumps({"error": "Faltan datos"})}

        # 1. Recuperar Memoria
        table = dynamodb.Table(TABLE_NAME)
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
            "lead_id": None   # ✅ NUEVO
        })

        # Detectar país
        pais_det = detectar_pais(user_question)
        if pais_det != "No definido":
            memory["country"] = pais_det

        safe_memory = convert_decimals(memory)

        s3_resp = s3.get_object(Bucket=BUCKET_NAME, Key=KNOWLEDGE_FILE)
        agency_knowledge = s3_resp["Body"].read().decode("utf-8")

        # 2. OpenAI
        system_prompt = f"""Eres María, asesora de MisVacacionesYa.
CONTEXTO AGENCIA: {agency_knowledge}
MEMORIA CLIENTE: {json.dumps(safe_memory)}
TU MISIÓN:
1. Responder dudas usando el CONTEXTO AGENCIA.
2. Si preguntan algo NO presente, responde: "Ese detalle lo coordinarás directamente con el asesor".
3. Obtener los 4 datos clave: destino, personas, fecha, presupuesto.

REGLAS DE ORO:
- Máximo 2 preguntas a la vez.
- No preguntar por datos ya conocidos.
- Si Estado HOT: Preguntar si prefiere WhatsApp o llamada.

RESPONDE SIEMPRE EN JSON:
{{
  "answer": "tu respuesta",
  "extracted_data": {{
    "destination": "valor o null", "people": "valor o null", "date": "valor o null", "budget": "valor o null"
  }}
}}
"""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            response_format={"type": "json_object"}
        )

        ai_response = json.loads(completion.choices[0].message.content)
        extracted = ai_response.get("extracted_data", {})

        # 3. Sincronizar Memoria
        for key in ["destination", "people", "date", "budget"]:
            val = extracted.get(key)
            if val and str(val).lower() not in ["null", "none"]:
                memory[key] = val

        # 4. Evaluación de Lead
        filled = sum([1 for k in ["destination", "people", "date", "budget"] if memory.get(k)])
        old_status = memory.get("lead_status", "cold")
        new_status = "hot" if filled == 4 else ("warm" if memory.get("destination") else "cold")

        # 5. CREAR LEAD (solo una vez)
        if new_status == "hot" and not memory.get("lead_sent") and BITRIX_WEBHOOK:

            mapa_destinos = {"españa": "1367", "roma": "1347", "italia": "1347", "argentina": "1207"}
            mapa_origenes = {"argentina": "263", "españa": "261"}

            dest_mem = str(memory.get("destination", "")).lower().strip()
            orig_mem = str(memory.get("country", "")).lower().strip()

            id_destino = mapa_destinos.get(dest_mem, "1213")
            id_origen = mapa_origenes.get(orig_mem, "")

            temp_history = memory.get("history", []) + [
                {"user": user_question, "assistant": ai_response.get("answer")}
            ]
            charla_texto = formatear_historial(temp_history)

            bitrix_payload = {
                "fields": {
                    "TITLE": f"Lead IA: {memory.get('destination')} - {user_id}",
                    "OPPORTUNITY": memory.get("budget"),
                    "UF_CRM_1729943385206": id_destino,
                    "UF_CRM_1729072409973": id_origen,
                    "DESCRIPTION": charla_texto,
                    "COMMENTS": charla_texto
                }
            }

            try:
                res = requests.post(f"{BITRIX_WEBHOOK}crm.lead.add.json", json=bitrix_payload, timeout=15)
                new_id = res.json().get("result")

                if new_id:
                    memory["lead_sent"] = True
                    memory["lead_id"] = new_id  # ✅ GUARDAMOS EL ID

                    base_url = BITRIX_WEBHOOK.split('/crm.lead.add.json')[0]
                    requests.post(
                        f"{base_url}/crm.timeline.comment.add.json",
                        json={
                            "fields": {
                                "ENTITY_ID": new_id,
                                "ENTITY_TYPE": "lead",
                                "COMMENT": charla_texto
                            }
                        }
                    )

            except Exception as b_err:
                print(f"Error en comunicación con Bitrix: {b_err}")

        # 6. UPDATE SI YA EXISTE
        elif new_status == "hot" and memory.get("lead_id") and BITRIX_WEBHOOK:

            lead_id = memory.get("lead_id")

            temp_history = memory.get("history", []) + [
                {"user": user_question, "assistant": ai_response.get("answer")}
            ]
            charla_texto = formatear_historial(temp_history)

            try:
                # actualizar datos
                requests.post(
                    f"{BITRIX_WEBHOOK}crm.lead.update.json",
                    json={
                        "id": lead_id,
                        "fields": {
                            "OPPORTUNITY": memory.get("budget")
                        }
                    },
                    timeout=10
                )

                # agregar nuevo mensaje al timeline
                base_url = BITRIX_WEBHOOK.split('/crm.lead.add.json')[0]
                requests.post(
                    f"{base_url}/crm.timeline.comment.add.json",
                    json={
                        "fields": {
                            "ENTITY_ID": lead_id,
                            "ENTITY_TYPE": "lead",
                            "COMMENT": f"NUEVO MENSAJE:\n{user_question}\n\nRespuesta IA:\n{ai_response.get('answer')}"
                        }
                    },
                    timeout=10
                )

            except Exception as e:
                print(f"Error actualizando lead: {e}")

        # 7. Guardar Memoria
        memory["lead_status"] = new_status
        history = memory.get("history", [])
        history.append({
            "user": user_question,
            "assistant": ai_response.get("answer")
        })
        memory["history"] = history[-5:]

        table.put_item(Item=convert_decimals(memory))

        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": ai_response.get("answer"),
                "lead_status": new_status
            })
        }

    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "answer": "Lo siento, tuve un error interno."
            })
        }