import json
import boto3
import os
import requests
import re
import uuid
import sys
import time
from openai import OpenAI
from decimal import Decimal
from datetime import datetime
import traceback

from service.helpers import (
    convert_decimals,
    extraer_telefono,
    detectar_pais,
    detectar_tipo_usuario,
    normalizar_extracciones,
    calcular_estado_presupuesto,
    formatear_historial
)

from service.config_service import (
    obtener_o_crear_configuracion,
    guardar_configuracion,
    es_administrador,
    puede_responder,
    obtener_configuracion,
    es_comando_admin
)

from service.memory_service import (
    obtener_memoria,
)

from service.whatsapp_service import (
    enviar_respuesta_whatcrm,
    responder_whatsapp
)

from service.prompt_service import (
    obtener_prompt,
    obtener_knowledge
)

from service.business_service import cargar_business_config

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

# --- CLIENTES ---
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

CHANNEL_POLICY = {
    "web": {
        "ask_phone": True,
        "require_phone_for_hot": True,
        "auto_hot": False
    },
    "whatsapp": {
        "ask_phone": False,
        "require_phone_for_hot": False,
        "auto_hot": True
    }
}

def lambda_handler(event, context):
    print("RAW EVENT:", json.dumps(event, default=str), flush=True)
    sys.stdout.flush()            
    try:
        # 0. Configuración Inicial
        TABLE_NAME             = os.environ.get("TABLE_NAME")
        BUCKET_NAME            = os.environ.get("BUCKET_NAME")
        KNOWLEDGE_FILE         = os.environ.get("KNOWLEDGE_FILE")
        BITRIX_WEBHOOK         = os.environ.get("BITRIX_WEBHOOK_URL")
        BUSINESS_FILE          = os.environ.get("BUSINESS_FILE", "business.json")
        PROMPT_FILE            = os.environ.get("PROMPT_FILE", "prompt.json")
        AUDIT_BUCKET           = os.environ.get("AUDIT_BUCKET")
        WHATCRM_INSTANCE       = os.environ.get("WHATCRM_INSTANCE")
        WHATCRM_TOKEN          = os.environ.get("WHATCRM_TOKEN")
        DEBUG_WHATSAPP         = os.environ.get("DEBUG_WHATSAPP", "false").lower() == "true"
        SEND_WHATSAPP_MESSAGES = os.environ.get("SEND_WHATSAPP_MESSAGES", "true").lower() == "true"
        CONFIG_TABLE_NAME      = os.environ.get("CONFIG_TABLE_NAME")
        SUPER_ADMIN_ID         = os.getenv("SUPER_ADMIN_ID")
        

        try:

            agency_knowledge = obtener_knowledge(
                BUCKET_NAME,
                KNOWLEDGE_FILE
            )
            
            prompt_config = obtener_prompt(
                BUCKET_NAME,
                PROMPT_FILE
            )
    
            business_config = cargar_business_config(
                BUCKET_NAME,
                BUSINESS_FILE
            )
            # ======================================
            # Parseo del body
            # ======================================
            raw_body = event.get("body", "{}")
            body = json.loads(raw_body)
        
            user_id = None
            user_question = None
            channel = None
        
            # ======================================
            # WEB
            # ======================================
            if "question" in body:
        
                print("Canal detectado: WEB")
        
                channel = "web"
                policy = business_config["channels"]["web"]
                user_id = body.get("user_id")
                user_question = body.get("question")
        
            # ======================================
            # WHATSAPP
            # ======================================
            elif "messages" in body:
        
                print("Canal detectado: WhatsApp")
        
                messages = body.get("messages", [])
        
                if len(messages) == 0:
                    raise Exception("No hay mensajes")
        
                mensaje = messages[0]

                # Detectar comandos administrativos antes de ignorar mensajes propios
                es_admin_command = es_comando_admin(
                    mensaje.get("body", "")
                )
        
                # Ignorar mensajes enviados por el bot
                if mensaje.get("fromMe") and not es_admin_command:
        
                    return {
                        "statusCode": 200,
                        "body": json.dumps({"ok": True})
                    }
        
                channel = "whatsapp"
                policy = business_config["channels"]["whatsapp"]
                
                if es_admin_command:
                    user_id = mensaje.get("from")
                else:
                    user_id = mensaje.get("chatId")
                
                user_question = mensaje.get("body")
        
            # ======================================
            # Formato desconocido
            # ======================================
            else:
        
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Formato de request no soportado"
                    })
                }
        
            # ======================================
            # Validaciones
            # ======================================
            if not user_id or not user_question:
        
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Faltan datos"
                    })
                }
        
            print(f"Canal: {channel}")
            print(f"Usuario: {user_id}")
            print(f"Pregunta: {user_question}")
        
        except Exception as parse_err:
        
            print("ERROR PARSEO")
            print(str(parse_err))
        
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": str(parse_err)
                })
            }

        # 1. Recuperar Memoria
        table = dynamodb.Table(TABLE_NAME)
        config_table = dynamodb.Table(CONFIG_TABLE_NAME)
        config = obtener_o_crear_configuracion(config_table)

        memory = obtener_memoria(
            table,
            user_id
        )
        
        nuevo_tipo = detectar_tipo_usuario(user_question)

        if nuevo_tipo != "lead":
            memory["user_type"] = nuevo_tipo
        elif not memory.get("user_type"):
            memory["user_type"] = "lead"        

        if channel == "whatsapp":
            numero_limpio = user_id.split('@')[0] if '@' in user_id else user_id
            memory["phone_contact"] = numero_limpio

        pais_det = detectar_pais(user_question)
        if pais_det != "No definido":
            memory["country"] = pais_det

        safe_memory = convert_decimals(memory)

        lead_fields = prompt_config.get(
            "lead_fields",
            ["destination", "people", "date", "budget"]
        )

        required_fields_count = len(lead_fields)

        faltantes = []

        for campo in lead_fields:
            if not memory.get(campo):
                faltantes.append(campo)
        
        faltantes_texto = ", ".join(faltantes)

        # 🚫 FILTRO DE TIPO DE USUARIO
        if memory.get("user_type") == "proveedor":
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "answer": "¡Hola! Para propuestas comerciales o colaboraciones, podés escribirnos por nuestros canales oficiales y un responsable se pondrá en contacto."
                })
            }

        if memory.get("user_type") == "cliente" and channel == "web":
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "answer": "¡Qué bueno tenerte de nuevo! Uno de nuestros asesores se contactará contigo..."
                })
            }
        
        # ======================================
        # Comandos de administración
        # ======================================

        if (
            channel == "whatsapp"
            and es_comando_admin(user_question)
        ):

            comando = user_question.strip().lower()

            if (
                comando != "#bot registrar"
                and not es_administrador(user_id, config)
            ):
                print("ADMIN 3 - Sin permisos")
                return {
                    "statusCode": 403,
                    "body": json.dumps({
                        "answer": "No tienes permisos para ejecutar este comando."
                    })
                }

            if comando == "#bot registrar":

                if config.get("admin_phone"):
                    return {
                        "statusCode": 200,
                        "body": json.dumps({
                            "answer": "Ya existe un administrador registrado."
                        })
                    }
            
                numero_admin = user_id.split("@")[0] if "@" in user_id else user_id
            
                config["admin_phone"] = numero_admin
            
                guardar_configuracion(config_table, config)
            
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "answer": "✅ Administrador registrado correctamente."
                    })
                }
        
            if comando == "#bot status":

                estado = "ACTIVO ✅" if config.get("bot_enabled", True) else "DESACTIVADO ⛔"
            
                admin = config.get("admin_phone") or "No registrado"
            
                respuesta = (
                    f"🤖 Estado: {estado}\n"
                    f"👤 Administrador: {admin}"
                )
            
                responder_whatsapp(
                    respuesta,
                    user_id,
                    SEND_WHATSAPP_MESSAGES,
                    WHATCRM_INSTANCE,
                    WHATCRM_TOKEN
                )
            
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "answer": respuesta
                    })
                }
            
            elif comando == "#bot off":

                config["bot_enabled"] = False
                guardar_configuracion(config_table, config)
        
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "answer": "✅ Bot desactivado."
                    })
                }
        
            elif comando == "#bot on":
        
                config["bot_enabled"] = True
                guardar_configuracion(config_table, config)
        
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "answer": "✅ Bot activado."
                    })
                }
        
        if not puede_responder(memory, config, channel):

            print("Bot deshabilitado para esta conversación.")
        
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "bot_disabled"
                })
            }
        
        # 2. OpenAI
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

        # 3. Sincronizar Memoria
        # phone_contact incluido en la sincronización
        campos_memoria = lead_fields.copy()

        if "phone_contact" not in campos_memoria:
            campos_memoria.append("phone_contact")

        if channel == "whatsapp" and not memory.get("phone_contact"):
           memory["phone_contact"] = user_id.split('@')[0]        
    
        
        for key in campos_memoria:
            val = extracted.get(key)
        
            if val and str(val).lower() not in ["null", "none"]:
        
                if key == "phone_contact" and channel == "whatsapp":
                    continue
        
                memory[key] = val

        if (
            memory.get("destination")
            and memory.get("people")
            and memory.get("date")
            and memory.get("budget_unknown")
            and policy["ask_phone"]
            and not memory.get("phone_contact")
        ):
            ai_response["answer"] = (
                "Entiendo! Si aún no cuentas con un presupuesto definido, "
                "uno de nuestros asesores puede orientarte sobre costos y opciones disponibles. "
                "Por favor indícanos un número de teléfono o un correo electrónico y nos pondremos en contacto contigo lo antes posible."
            )
        
        if (
            memory.get("budget_unknown")
            and memory.get("phone_contact")
        ):
        
            ai_response["answer"] = (
                "Perfecto. Hemos recibido tu número de contacto. "
                "Uno de nuestros asesores se comunicará contigo lo antes posible para ayudarte a evaluar opciones y presupuesto para tu viaje."
            )        

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
            memory["budget_status"] == "low"
            and memory.get("destination")
            and memory.get("people")
            and memory.get("date")
            and policy["ask_phone"]
            and not memory.get("phone_contact")
        ):

           ai_response["answer"] = (
               "Gracias por compartir los datos de tu viaje. "
               "Para el destino y la cantidad de viajeros indicados, el presupuesto podría resultar ajustado según las fechas y la disponibilidad. "
               "Si lo deseas, déjanos un número de contacto o un correo electrónico y un asesor se comunicará contigo lo antes posible para ayudarte a encontrar mejores opciones."
            )
           
        elif (
            memory["budget_status"] == "low"
            and memory.get("phone_contact")
        ):
            ai_response["answer"] = (
                "Perfecto. Hemos recibido tu número de contacto. "
                "Un asesor se comunicará contigo lo antes posible."
            )   

        # 4. Evaluación de Lead
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
                (filled == required_fields_count and memory.get("phone_contact") and policy["require_phone_for_hot"])
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
        
        respuesta = ai_response.get("answer")

        history.append({
            "user": user_question,
            "assistant": respuesta if respuesta else ""
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

        # ======================================
        # Respuesta según canal
        # ======================================
        
        if channel == "whatsapp":

            respuesta_texto = ai_response.get("answer", "")
        
            responder_whatsapp(
                respuesta_texto,
                user_id,
                SEND_WHATSAPP_MESSAGES,
                WHATCRM_INSTANCE,
                WHATCRM_TOKEN
            )
        
            debug_response = {
                "status": "sent"
            }
            if DEBUG_WHATSAPP:
                debug_response.update({
                    "answer": ai_response.get("answer"),
                    "memory": convert_decimals(memory),
                    "lead_status": memory.get("lead_status"),
                    "user_type": memory.get("user_type"),
                    "budget_status": memory.get("budget_status"),
                    "channel": channel,
                    "lead_sent": memory.get("lead_sent"),
                    "lead_id": memory.get("lead_id"),
                    "phone_contact": memory.get("phone_contact"),
                    "budget_unknown": memory.get("budget_unknown"),
                    "send_whatsapp_messages": SEND_WHATSAPP_MESSAGES
                })

            return {
                "statusCode": 200,
                "body": json.dumps(
                    convert_decimals(debug_response)
                )
            }
        
        elif channel == "web":
        
            return {
                "statusCode": 200,
                "body": json.dumps({
                "answer": ai_response.get("answer")
                })
            }
        
        else:
        
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Canal desconocido"
                })
            }

    except Exception as e:
        print("========== ERROR GENERAL ==========")
        traceback.print_exc()
    
        return {
            "statusCode": 500,
            "body": json.dumps({
                "answer": "Lo siento, tuve un error interno."
            })
        }