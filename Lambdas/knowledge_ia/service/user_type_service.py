import json


def validar_tipo_usuario(memory, channel, business_config):

    if memory.get("user_type") == "proveedor":
        return (
            "¡Hola! Para propuestas comerciales o colaboraciones, "
            "podés escribirnos por nuestros canales oficiales y un "
            "responsable se pondrá en contacto."
        )

    if memory.get("user_type") == "cliente":

        if channel == "whatsapp":
            return (
                "¡Qué bueno tenerte de nuevo! "
                "Uno de nuestros asesores continuará la conversación contigo a la brevedad."
            )

        if channel == "web":

            whatsapp = business_config.get("whatsapp")

            if whatsapp:
                return (
                    "¡Qué bueno saber que ya viajaste con nosotros! 😊 "
                    f"Para brindarte una atención personalizada, escribinos por WhatsApp al {whatsapp} "
                    "y uno de nuestros asesores continuará con tu consulta."
                )

            return (
                "¡Qué bueno saber que ya viajaste con nosotros! 😊 "
                "Para brindarte una atención personalizada, comunicate con nosotros por nuestro canal de WhatsApp."
            )

    return None