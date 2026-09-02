from service.memory_service import sincronizar_memoria
from service.business_rules_engine import aplicar_reglas_negocio




def actualizar_memoria(
    memory,
    extracted,
    user_question,
    ai_response,
    required_fields,
    policy,
    channel,
    business_config,
):

    optional_fields = business_config.get(
        "optional_fields",
        []
    )

    print(
        "=== DATOS EXTRAIDOS ANTES DE SYNC ===",
        extracted
    )
    
    memory = sincronizar_memoria(
        memory=memory,
        extracted=extracted,
        required_fields=required_fields,
        optional_fields=optional_fields,
        channel=channel,
        ai_response=ai_response,
    )

    memory = aplicar_reglas_negocio(
        memory=memory,
        ai_response=ai_response,
        policy=policy,
        user_question=user_question,
        business_config=business_config,
        channel=channel,
    )
    
    return memory