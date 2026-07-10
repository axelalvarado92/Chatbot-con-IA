from datetime import datetime
from zoneinfo import ZoneInfo


def esta_en_horario_laboral(business_config):

    business = business_config.get("business", {})

    horario = business.get("working_hours", {})

    if not horario.get("enabled", False):
        return True

    timezone = business.get(
        "timezone",
        "UTC"
    )

    ahora = datetime.now(
        ZoneInfo(timezone)
    )

    dias = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday"
    ]

    dia = dias[ahora.weekday()]

    horario_dia = horario.get(dia)

    if horario_dia is None:
        return False
    
    hora_actual = ahora.strftime("%H:%M")
    
    return (
        horario_dia["start"]
        <= hora_actual
        <= horario_dia["end"]
    )