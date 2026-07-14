import json


def validar_tipo_usuario(memory, channel):

    if memory.get("user_type") == "proveedor":
        return (
            "¡Hola! Para propuestas comerciales o colaboraciones, "
            "podés escribirnos por nuestros canales oficiales y un "
            "responsable se pondrá en contacto."
        )

    if (
        memory.get("user_type") == "cliente"
        and channel == "web"
    ):
        return (
            "¡Qué bueno tenerte de nuevo! "
            "Uno de nuestros asesores se contactará contigo..."
        )

    return None