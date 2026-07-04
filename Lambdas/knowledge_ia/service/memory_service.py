from service.helpers import convert_decimals

def obtener_memoria(table, user_id):
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
        "human_agent": False,
        "user_type": None,
        "phone_contact": None,
        "budget_status": None,
        "budget_known": False,
        "name": None,
    })

    return memory