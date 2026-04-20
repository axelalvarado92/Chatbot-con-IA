import json
import os
import boto3
import requests

s3 = boto3.client('s3')

API_KEY = os.environ.get("OPENAI_API_KEY")


def get_knowledge():
    bucket = os.environ.get("BUCKET_NAME")
    key = os.environ.get("KNOWLEDGE_FILE")

    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    return json.loads(content)


def build_context(knowledge):
    context = ""
    for item in knowledge:
        context += f"- {item.get('answer', '')}\n"
    return context


def ask_model(question, context):
    prompt = f"""
Sos un asesor de ventas de una agencia de viajes.

Tu objetivo es ayudar al cliente y guiarlo para concretar un viaje.

Reglas:
- Respondé de forma clara, cercana y amigable
- Hacé preguntas para entender mejor al cliente
- Recomendá opciones basadas en la información disponible
- Si falta información, pedí datos como fechas, presupuesto o cantidad de personas
- No inventes información que no esté en el contexto
- Siempre intentá cerrar con una acción (por ejemplo: ofrecer ayuda de un asesor o cotización)

Información disponible:
{context}

Cliente dice:
{question}
"""

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "input": prompt,
            "temperature": 0.4
        }
    )

    result = response.json()
    print("OPENAI RESPONSE:", result)

    if "output" not in result:
        return f"Hubo un problema procesando la respuesta."

    return result["output"][0]["content"][0]["text"]


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        question = body.get("question", "")

        if not question:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta la pregunta"}, ensure_ascii=False)
            }

        knowledge = get_knowledge()
        context_text = build_context(knowledge)

        answer = ask_model(question, context_text)

        return {
            "statusCode": 200,
            "body": json.dumps({"answer": answer}, ensure_ascii=False)
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno del servidor"}, ensure_ascii=False)
        }