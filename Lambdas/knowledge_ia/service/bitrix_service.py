import requests
from service.helpers import formatear_historial

def enviar_lead_bitrix(
    memory,
    user_id,
    user_question,
    ai_response,
    new_status,
    business_config,
    BITRIX_WEBHOOK
):
    if new_status == "hot" and not memory.get("lead_sent") and BITRIX_WEBHOOK:

        crm_config = business_config.get(
            "crm",
            {}
        )
        
        mapa_destinos = crm_config.get(
            "destination_mapping",
            {}
        )
        
        mapa_origenes = crm_config.get(
            "origin_mapping",
            {}
        )
        
        dest_mem = str(memory.get("destination", "")).lower().strip()
        orig_mem = str(memory.get("country", "")).lower().strip()
        id_destino = mapa_destinos.get(dest_mem, "1213")
        id_origen = mapa_origenes.get(orig_mem, "")
        temp_history = memory.get("history", []) + [
            {"user": user_question, "assistant": ai_response.get("answer")}
        ]
        charla_texto = formatear_historial(
            temp_history,
            business_config["assistant_name"]
        )
        fields = {
            "TITLE": f"{business_config['company_name']} - {user_id}",
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
            business_config["assistant_name"]
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