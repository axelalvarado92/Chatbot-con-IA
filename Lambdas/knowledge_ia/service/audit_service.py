import json
import uuid
import boto3

from datetime import datetime

from service.helpers import convert_decimals
s3 = boto3.client("s3")

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