import json
import boto3
import os
import requests
import re
from openai import OpenAI
from decimal import Decimal
from datetime import datetime
import uuid
import re

def guardar_auditoria(
    bucket,
    user_id,
    user_question,
    ai_answer,
    memory,
    lead_status
):
    try:

        timestamp = datetime.utcnow()

        audit_record = {
            "timestamp": timestamp.isoformat(),
            "user_id": user_id,
            "user_message": user_question,
            "assistant_answer": ai_answer,
            "lead_status": lead_status,
            "budget_status": memory.get("budget_status"),
            "memory_snapshot": memory
        }

        key = (
            f"{timestamp.year}/"
            f"{timestamp.month:02d}/"
            f"{timestamp.day:02d}/"
            f"{uuid.uuid4()}.json"
        )

        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(
                convert_decimals(audit_record),
                ensure_ascii=False
            ),
            ContentType="application/json"
        )

    except Exception as e:
        print(f"Error guardando auditoría: {e}")

# --- UTILIDADES ---
def detectar_tipo_usuario(texto):
    t = texto.lower()

    if any(p in t for p in ["proveedor", "hotel", "agencia", "partner", "colaboración"]):
        return "proveedor"

    if any(p in t for p in ["ya viaje", "ya viajé", "cliente", "viaje con ustedes", "compré", "compre"]):
        return "cliente"

    return "lead"

def formatear_historial(history, assistant_name="Asistente"):
    if not history:
        return "No hay historial previo."

    texto = f"--- CONVERSACIÓN CON IA {assistant_name.upper()} ---\n"

    for msg in history:
        u = msg.get('user', 'Usuario')
        a = msg.get('assistant', assistant_name)

        texto += f"Cliente: {u}\n"
        texto += f"Asistente: {a}\n"
        texto += "----------------\n"

    return texto

def convert_decimals(obj):
    if isinstance(obj, list): return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict): return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal): return int(obj) if obj % 1 == 0 else float(obj)
    return obj

def detectar_pais(texto):
    t = texto.lower()

    if any(p in t for p in ["argentina", "argentino", "arg"]):
        return "Argentina"

    if any(p in t for p in ["españa", "español", "espania", "espańa"]):
        return "España"

    return "No definido"

def extraer_telefono(texto):

    patron = r'(\+?\d[\d\s\-\(\)]{7,20}\d)'

    match = re.search(patron, texto)

    if match:
        return match.group(1)

    return None

def calcular_estado_presupuesto(destination, people, budget):

    if not destination or not people or not budget:
        return None

    try:

        print(f"Destino recibido: {destination}")
        print(f"Personas recibidas: {people}")
        print(f"Budget recibido: {budget}")

        destino = str(destination).lower().strip()

        budget_clean = re.sub(
            r"[^\d]",
            "",
            str(budget)
        )

        presupuesto_total = float(budget_clean)

        viajeros = int(people)

        MIN_BUDGETS = {
            "china": 5000,
            "japon": 6000,
            "japón": 6000,
            "egipto": 3500,
            "turquia": 4000,
            "turquía": 4000,
            "grecia": 4000,
            "españa": 4500,
            "espana": 4500,
            "italia": 4500
        }

        minimo_persona = MIN_BUDGETS.get(destino)

        if not minimo_persona:
            return None

        minimo_total = minimo_persona * viajeros

        print(f"Presupuesto limpio: {presupuesto_total}")
        print(f"Minimo requerido: {minimo_total}")

        if presupuesto_total < minimo_total:
            return "low"

        elif presupuesto_total < minimo_total * 1.3:
            return "adjusted"

        else:
            return "good"

    except:
        print(f"ERROR PRESUPUESTO: {e}")
        return None

# --- CLIENTES ---
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def lambda_handler(event, context):            
    try:
        # 0. Configuración Inicial
        TABLE_NAME     = os.environ.get("TABLE_NAME")
        BUCKET_NAME    = os.environ.get("BUCKET_NAME")
        KNOWLEDGE_FILE = os.environ.get("KNOWLEDGE_FILE")
        BITRIX_WEBHOOK = os.environ.get("BITRIX_WEBHOOK_URL")
        BUSINESS_TYPE  = os.environ.get("BUSINESS_TYPE", "travel")
        PROMPT_FILE    = os.environ.get("PROMPT_FILE", "prompt.json")
        AUDIT_BUCKET   = os.environ.get("AUDIT_BUCKET")

        raw_body = event.get("body", "")

        try:
            body = json.loads(raw_body)
            # 1: eliminada la detección de WhatCRM, un solo formato
            user_id = body.get("user_id")
            user_question = body.get("question")
        except:
            user_id = None
            user_question = None

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
            "lead_id": None,
            "user_type": None,
            "phone_contact": None,
            "budget_status": None,
            "budget_known": False
        })
        nuevo_tipo = detectar_tipo_usuario(user_question)

        if nuevo_tipo != "lead":
            memory["user_type"] = nuevo_tipo
        elif not memory.get("user_type"):
            memory["user_type"] = "lead"        

        pais_det = detectar_pais(user_question)
        if pais_det != "No definido":
            memory["country"] = pais_det

        safe_memory = convert_decimals(memory)

        s3_resp = s3.get_object(Bucket=BUCKET_NAME, Key=KNOWLEDGE_FILE)
        agency_knowledge = s3_resp["Body"].read().decode("utf-8")

        prompt_resp = s3.get_object(
            Bucket=BUCKET_NAME,
            Key=PROMPT_FILE
        )
        
        prompt_config = json.loads(
            prompt_resp["Body"].read().decode("utf-8")
        )

        lead_fields = prompt_config.get(
            "lead_fields",
            ["destination", "people", "date", "budget"]
        )

        lead_fields = prompt_config.get(
            "lead_fields",
            ["destination", "people", "date", "budget"]
        )        
        
        required_fields_count = len(lead_fields)

        # 🚫 FILTRO DE TIPO DE USUARIO
        if memory.get("user_type") == "proveedor":
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "answer": "¡Hola! Para propuestas comerciales o colaboraciones, podés escribirnos por nuestros canales oficiales y un responsable se pondrá en contacto."
                })
            }

        if memory.get("user_type") == "cliente":
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "answer": "¡Qué bueno tenerte de nuevo! Uno de nuestros asesores se contactará contigo lo antes posible para ayudarte en lo que necesites."
                })
            }

        # 2. OpenAI
        system_prompt = f"""
CONTEXTO AGENCIA: {agency_knowledge}
Eres {prompt_config['assistant_name']},
asesora de viajes de {prompt_config['company_name']}.

MEMORIA CLIENTE:
{json.dumps(safe_memory)}

ESTADO PRESUPUESTO:
{memory.get("budget_status")}

TU MISIÓN:
{chr(10).join(prompt_config['mission'])}

REGLAS DE RECOMENDACIÓN:
{chr(10).join(prompt_config['recommendation_rules'])}

REGLaS DE EXTRACCIÓN DE DATOS:
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
        print("USER:", user_question)
        print("EXTRACTED:", extracted)
        
        telefono_detectado = extraer_telefono(user_question)

        if telefono_detectado:
            extracted["phone_contact"] = telefono_detectado

        # 3. Sincronizar Memoria
        # phone_contact incluido en la sincronización
        campos_memoria = lead_fields.copy()

        if "phone_contact" not in campos_memoria:
            campos_memoria.append("phone_contact")
        
        for key in campos_memoria:
            val = extracted.get(key)

            if val and str(val).lower() not in ["null", "none"]:
                memory[key] = val

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
            memory.get("destination")
            and memory.get("people")
            and memory.get("date")
            and memory.get("budget_unknown")
            and not memory.get("phone_contact")
        ):
            ai_response["answer"] = (
                "Entiendo! Si aún no cuentas con un presupuesto definido, "
                "uno de nuestros asesores puede orientarte sobre costos y opciones disponibles. "
                "Por favor indícanos un número de teléfono y nos pondremos en contacto contigo lo antes posible."
            )
        
        if (
            memory.get("budget_unknown")
            and memory.get("phone_contact")
        ):
        
            ai_response["answer"] = (
                "Perfecto. Hemos recibido tu número de contacto. "
                "Uno de nuestros asesores se comunicará contigo lo antes posible para ayudarte a evaluar opciones y presupuesto para tu viaje."
            )

        if (    
            memory["budget_status"] == "low"
            and memory.get("destination")
            and memory.get("people")
            and memory.get("date")
            and memory.get("budget")
        ):

           ai_response["answer"] = (
               "Gracias por compartir los datos de tu viaje. "
               "Para el destino y la cantidad de viajeros indicados, el presupuesto podría resultar ajustado según las fechas y la disponibilidad. "
               "Si lo deseas, déjanos un número de contacto y un asesor se comunicará contigo lo antes posible para ayudarte a encontrar mejores opciones."
            )

        # 4. Evaluación de Lead
        filled = sum(
            1
            for k in lead_fields
            if memory.get(k)
        )
        budget_status = memory.get("budget_status")

        # HOT requiere los 4 datos + teléfono de contacto
        if BUSINESS_TYPE == "travel":

            budget_status = memory.get("budget_status")

            if (
                (
                    filled == required_fields_count
                    and memory.get("phone_contact")
                )
                or
                (
                    memory.get("destination")
                    and memory.get("people")
                    and memory.get("date")
                    and memory.get("budget_unknown")
                    and memory.get("phone_contact")
                )
            ):
                new_status = "hot"
            
            elif (
                memory.get("destination")
                and memory.get("people")
                and memory.get("date")
                and memory.get("budget_unknown")
                and memory.get("phone_contact")
            ):
                new_status = "hot"

            elif (
                memory.get("destination")
                or memory.get("budget")
                or memory.get("people")
                or memory.get("date")
            ):
                new_status = "warm"

            else:
                new_status = "cold"
        
        else:
        
            if filled == 4:
                new_status = "hot"
            elif filled > 0:
                new_status = "warm"
            else:
                new_status = "cold"

        # 5. CREAR LEAD EN BITRIX (solo una vez cuando llega a HOT)
        if new_status == "hot" and not memory.get("lead_sent") and BITRIX_WEBHOOK:

            mapa_destinos = {"españa": "1367",
                            "roma": "1347",
                            "italia": "1347",
                            "argentina": "1207",
                            "china": "1765",
                            "japon": "1081",
                            "francia": "1817",
                            "grecia": "1977",
                            "egipto": "1507",
                            "turquia": "1687",
                            "corea del sur": "1083",
                            "dubai": "1477",
                            "marruecos": "1377",
                            "india": "1085"
                            }
            
            mapa_origenes = {"argentina": "263", "españa": "261"}

            dest_mem = str(memory.get("destination", "")).lower().strip()
            orig_mem = str(memory.get("country", "")).lower().strip()

            id_destino = mapa_destinos.get(dest_mem, "1213")
            id_origen = mapa_origenes.get(orig_mem, "")

            temp_history = memory.get("history", []) + [
                {"user": user_question, "assistant": ai_response.get("answer")}
            ]
            charla_texto = formatear_historial(
                temp_history,
                prompt_config["assistant_name"]
            )

            fields = {
                "TITLE": f"{prompt_config['company_name']} - {user_id}",
                "OPPORTUNITY": memory.get("budget"),
                "UF_CRM_1729943385206": id_destino,
                "UF_CRM_1729072409973": id_origen,
                "DESCRIPTION": charla_texto,
                "COMMENTS": charla_texto
            }

            if memory.get("budget_unknown"):
                fields["COMMENTS"] += "\n\nPresupuesto: NO DEFINIDO POR EL CLIENTE"

            if memory.get("phone_contact"):
                fields["PHONE"] = [{
                    "VALUE": memory.get("phone_contact"),
                    "VALUE_TYPE": "WORK"
                }]

            bitrix_payload = {
                "fields": fields
            }

            try:
                res = requests.post(f"{BITRIX_WEBHOOK}crm.lead.add.json", json=bitrix_payload, timeout=15)
                new_id = res.json().get("result")

                if new_id:
                    memory["lead_sent"] = True
                    memory["lead_id"] = new_id
                    memory["budget_unknown"] = False

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

        # 6. UPDATE SI EL LEAD YA EXISTE
        elif new_status == "hot" and memory.get("lead_id") and BITRIX_WEBHOOK:

            lead_id = memory.get("lead_id")

            temp_history = memory.get("history", []) + [
                {"user": user_question, "assistant": ai_response.get("answer")}
            ]
            charla_texto = formatear_historial(
                temp_history,
                prompt_config["assistant_name"]
            )
            

            try:
                requests.post(
                    f"{BITRIX_WEBHOOK}crm.lead.update.json",
                    json={
                        "id": lead_id,
                       "fields": {
                            "OPPORTUNITY": memory.get("budget"),
                            "PHONE": [
                                {
                                    "VALUE": memory.get("phone_contact"),
                                    "VALUE_TYPE": "WORK"
                                }
                            ]
                        }
                    },
                    timeout=10
                )

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
        memory["history"] = history[-20:]

        table.put_item(Item=convert_decimals(memory))

        if AUDIT_BUCKET:

            guardar_auditoria(
                AUDIT_BUCKET,
                user_id,
                user_question,
                ai_response.get("answer"),
                memory,
                new_status
            )

        # 7: return unificado, eliminado el bloque condicional de WhatCRM
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