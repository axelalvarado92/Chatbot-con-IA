import boto3
import os


def obtener_configuracion(config_table):

    response = config_table.get_item(
        Key={
            "config_id": "global"
        }
    )

    return response.get("Item")

def obtener_o_crear_configuracion(
    config_table,
    business_config
   ):

    config = obtener_configuracion(config_table)

    if config:
        return config

    config = {
        "config_id": "global",
    
        # Estado del bot
        "bot_enabled": True,
        "maintenance_mode": False,
    
        # Administración
        "admin_phone": business_config.get("admin_phone"),

        "business_timezone": business_config.get(
            "timezone",
            "UTC"
        )
    }
    
    print("Configuración global creada.")
    config_table.put_item(Item=config)

    return config

def guardar_configuracion(config_table, config):

    config_table.put_item(
        Item=config
    )



