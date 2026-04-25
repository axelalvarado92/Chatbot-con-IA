import json
import boto3
import os
import requests
from openai import OpenAI

# Configuración de clientes
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def lambda_handler(event, context):
    try:
        # 1. Obtener datos de entrada
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("user_id")
        user_question = body.get("question")
        
        if not user_id or not user_question:
            return {"statusCode": 400, "body": json.dumps({"error": "Faltan user_id o question"})}

        # 2. Obtener Memoria de DynamoDB
        table = dynamodb.Table(os.environ.get("TABLE_NAME"))
        response = table.get_item(Key={"user_id": user_id})
        memory = response.get("item", {
            "user_id": user_id,
            "destination": None,
            "people": None,
            "date": None,
            "budget": None,
            "room_type": None,
            "lead_status": "warm"
        })

        # 3. Obtener Conocimiento de S3
        bucket_name = os.environ.get("BUCKET_NAME")
        knowledge_key = os.environ.get("KNOWLEDGE_FILE")
        s3_resp = s3.get_object(Bucket=bucket_name, Key=knowledge_key)
        agency_knowledge = s3_resp["Body"].read().decode("utf-8")

        # 4. Prompt para OpenAI con Estrategia de Goteo
        system_prompt = f"""
        Eres Axel, asesor experto de Babel Viajes. 
        CONTEXTO AGENCIA: {agency_knowledge}
        DATOS ACTUALES DEL CLIENTE: {json.dumps(memory)}

        TU MISIÓN:
        Completa el perfil del cliente de forma CONVERSACIONAL. 
        
        REGLAS DE INTERACCIÓN:
        1. PRIORIDAD: No hagas más de 2 preguntas por mensaje.
        2. FLUJO: 
           - Si no sabes el destino, empieza por ahí.
           - Si ya sabes el destino, pregunta fechas y cantidad de personas.
           - Por último, indaga sobre el presupuesto y el tipo de habitación.
        3. EMPATÍA: Haz comentarios breves y positivos sobre los destinos que elija el cliente.

        RESPONDE SIEMPRE EN ESTE FORMATO JSON:
        {{
          "answer": "tu respuesta al cliente",
          "extracted_data": {{
             "destination": "valor o null",
             "people": "valor o null",
             "date": "valor o null",
             "budget": "valor o null",
             "room_type": "valor o null"
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

        # 5. Actualizar memoria con nuevos datos extraídos
        for key in ["destination", "people", "date", "budget", "room_type"]:
            if extracted.get(key):
                memory[key] = extracted[key]

        # 6. LÓGICA DE LEAD STATUS REFORZADA
        def is_valid(value):
            banned = ["null", "none", "", "unknown", "por definir", "no especificado"]
            return value is not None and str(value).lower().strip() not in banned

        dest = memory.get("destination")
        peop = memory.get("people")
        date = memory.get("date")
        budg = memory.get("budget")

        # Verificamos si los 4 pilares críticos están presentes
        is_ready = is_valid(dest) and is_valid(peop) and is_valid(date) and is_valid(budg)
        
        # Cambio a HOT solo si es la primera vez que se completan los datos
        should_trigger_webhook = False
        if is_ready and memory.get("lead_status") != "hot":
            memory["lead_status"] = "hot"
            should_trigger_webhook = True

        # 7. Guardar en DynamoDB
        table.put_item(Item=memory)

        # 8. Envío a Bitrix si el Lead está HOT
        if should_trigger_webhook:
            webhook_url = os.environ.get("BITRIX_WEBHOOK_URL")
            if webhook_url:
                payload = {
                    "fields": {
                        "TITLE": f"Lead Calificado: {user_id}",
                        "COMMENTS": f"Destino: {dest}, Personas: {peop}, Fecha: {date}, Presupuesto: {budg}"
                    }
                }
                requests.post(webhook_url, json=payload)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": ai_response.get("answer"),
                "lead_status": memory["lead_status"],
                "should_contact": should_trigger_webhook
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno en la Lambda"})
        }