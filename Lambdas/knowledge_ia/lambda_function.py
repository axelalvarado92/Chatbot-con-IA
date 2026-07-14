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

from service.app_config_service import (
    cargar_settings
)

from service.user_type_service import (
    validar_tipo_usuario
)

from service.ai_service import (
    obtener_respuesta_ai,
)

from service.user_context_service import (
    preparar_contexto_usuario
)

from service.request_service import (
    parse_request
)

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
    obtener_configuracion,
    
)

from service.lead_service import (
    calcular_estado_lead,
    obtener_campos_faltantes
)

from service.bot_control_service import (
    puede_responder,
    es_administrador,
    es_comando_admin
)

from service.memory_service import (
    obtener_memoria,
    actualizar_campos_basicos,
    sincronizar_memoria,
    guardar_memoria
)

from service.memory_update_service import actualizar_memoria

from service.audit_service import (
    guardar_auditoria
)

from service.whatsapp_service import (
    enviar_respuesta_whatcrm,
    responder_whatsapp,
    procesar_comando_admin
)

from service.prompt_service import (
    obtener_prompt,
)

from service.knowledge_service import (
    obtener_knowledge
)

from service.business_service import cargar_business_config

from service.business_hours_service import (
    esta_en_horario_laboral
)

from service.bitrix_service import enviar_lead_bitrix

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
    
    # =====================================================
    # 0. Inicialización de la aplicación
    # =====================================================
    
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

        

        try:
            
            settings = cargar_settings(
                BUCKET_NAME,
                PROMPT_FILE,
                KNOWLEDGE_FILE,
                BUSINESS_FILE
            )
            
            agency_knowledge = settings["knowledge"]
            prompt_config = settings["prompt"]
            business_config = settings["business"]

            table = dynamodb.Table(TABLE_NAME)
            
            config_table = dynamodb.Table(CONFIG_TABLE_NAME)
            
            config = obtener_o_crear_configuracion(
                    config_table,
                    business_config
                )
            
            
     # =====================================================
     # 1. Recepción y validación de la solicitud
     # =====================================================
            # Parseo del body
            raw_body = event.get("body", "{}")
            body = json.loads(raw_body)

            # Eventos ACK de WhatCRM
            if "acks" in body:
            
                print("Evento ACK ignorado")
            
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "status": "ack_ignored"
                    })
                }
        
            user_id = None
            chat_id = None
            user_question = None
            channel = None
        
            request = parse_request(
                body,
                business_config
            )
            
            if request is None:
            
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "ok": True
                    })
                }
            
            channel = request["channel"]
            policy = request["policy"]
            user_id = request["user_id"]
            chat_id = request["chat_id"]
            user_question = request["question"]
            
            print(f"Canal: {channel}")
            print(f"Usuario: {user_id}")
            print(f"Chat: {chat_id}")
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
    
    # =====================================================
    # 2. Preparar contexto del usuario
    # =====================================================
        # Recuperar Memoria
        memory = preparar_contexto_usuario(
            table=table,
            user_id=user_id,
            user_question=user_question
        )
       
    # =====================================================
    # 3. Analizar estado del lead
    # =====================================================
        lead_fields, faltantes = obtener_campos_faltantes(
            memory,
            prompt_config
        )
        
        faltantes_texto = ", ".join(faltantes)

        # FILTRO DE TIPO DE USUARIO
        mensaje = validar_tipo_usuario(
            memory,
            channel
        )
        
        if mensaje:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "answer": mensaje
                })
            }
        
    # =====================================================
    # 4. Validaciones previas al procesamiento
    # =====================================================
        # Comandos de administración
        print("Pregunta:", repr(user_question))
        print("Es comando:", es_comando_admin(user_question))

        if (
            channel == "whatsapp"
            and es_comando_admin(user_question)
        ):

            respuesta = procesar_comando_admin(
                comando=user_question,
                user_id=user_id,
                config=config,
                config_table=config_table,
                business_config=business_config,
                bucket_name=BUCKET_NAME,
                business_file=BUSINESS_FILE,
                send_messages=SEND_WHATSAPP_MESSAGES,
                instance=WHATCRM_INSTANCE,
                token=WHATCRM_TOKEN,

            )
            
            if respuesta:
                return respuesta
            
        if not puede_responder(memory, config, channel):

            print("Bot deshabilitado para esta conversación.")
        
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "bot_disabled"
                })
            }
        
        # Validar horario laboral  
        if (
            channel == "whatsapp"
            and not esta_en_horario_laboral(business_config)
        ):
        
            business = business_config.get("business", {})

            respuesta = business.get(
                "outside_hours_message",
                "🕒 En este momento estamos fuera de nuestro horario de atención."
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

    # =====================================================
    # 5. Generación de respuesta con IA
    # =====================================================
        ai_response = obtener_respuesta_ai(
            client=client,
            prompt_config=prompt_config,
            agency_knowledge=agency_knowledge,
            memory=memory,
            user_question=user_question,
            faltantes_texto=faltantes_texto
        )

        extracted = ai_response.get("extracted_data", {})
    
    # =====================================================
    # 6. Actualización del contexto del usuario
    # =====================================================
        # Actualizar Memoria
        memory = actualizar_memoria(
            memory=memory,
            extracted=extracted,
            user_question=user_question,
            ai_response=ai_response,
            lead_fields=lead_fields,
            policy=policy,
            channel=channel
        )
   
    # =====================================================
    # 7. Calificación y sincronización del lead
    # =====================================================
        # Evaluación de Lead
        new_status = calcular_estado_lead(
            memory=memory,
            lead_fields=lead_fields,
            channel=channel,
            policy=policy
        )


        # 5. CREAR LEAD EN BITRIX
        enviar_lead_bitrix(
            memory=memory,
            user_id=user_id,
            user_question=user_question,
            ai_response=ai_response,
            new_status=new_status,
            prompt_config=prompt_config,
            BITRIX_WEBHOOK=BITRIX_WEBHOOK
        )

    # =====================================================
    # 8. Persistencia
    # =====================================================    
        # 6. Guardar Memoria
        guardar_memoria(
            table=table,
            memory=memory,
            user_question=user_question,
            ai_response=ai_response,
            new_status=new_status
         )

        if AUDIT_BUCKET:

            guardar_auditoria(
                bucket=AUDIT_BUCKET,
                user_id=user_id,
                user_question=user_question,
                ai_answer=ai_response.get("answer"),
                memory=memory,
                lead_status=new_status
            )

    # =====================================================
    # 9. Envío de la respuesta
    # =====================================================
        
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
        
    # =====================================================
    # Manejo global de errores
    # =====================================================

    except Exception as e:
        print("========== ERROR GENERAL ==========")
        traceback.print_exc()
    
        return {
            "statusCode": 500,
            "body": json.dumps({
                "answer": "Lo siento, tuve un error interno."
            })
        }