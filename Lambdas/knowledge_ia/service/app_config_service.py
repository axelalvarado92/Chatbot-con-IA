from service.prompt_service import obtener_prompt
from service.knowledge_service import obtener_knowledge
from service.business_service import cargar_business_config


def cargar_settings(
    bucket_name,
    prompt_file,
    knowledge_file,
    business_file
):

    return {

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