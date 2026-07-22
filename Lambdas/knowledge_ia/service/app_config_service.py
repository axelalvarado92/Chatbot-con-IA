from service.prompt_service import obtener_prompt
from service.knowledge_service import obtener_knowledge
from service.business_service import cargar_business_config

_SETTINGS_CACHE = None


def cargar_settings(
    bucket_name,
    prompt_file,
    knowledge_file,
    business_file
):

    global _SETTINGS_CACHE

    if _SETTINGS_CACHE:
        print("Usando configuración en caché.")
        return _SETTINGS_CACHE
    
    print("Cargando configuración desde S3...")

    _SETTINGS_CACHE = {

        "prompt": obtener_prompt(
            bucket_name,
            prompt_file
        ),

        "knowledge": obtener_knowledge(
            bucket_name,
            knowledge_file
        ),

        "business": cargar_business_config(
            bucket_name,
            business_file
        )
    }

    return _SETTINGS_CACHE