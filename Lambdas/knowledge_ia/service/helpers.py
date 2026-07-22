import re

from decimal import Decimal
# --- UTILIDADES ---

def detectar_tipo_usuario(texto):
    t = texto.lower()

    if any(p in t for p in [
        "soy proveedor",
        "quiero ofrecer",
        "quiero vender",
        "colaboración",
        "colaborar",
        "partner",
        "alianza",
        "represento",
        "hotel",
        "operador",
        "mayorista",
        "agencia de viajes",
        "proveedor"]):
        return "proveedor"

    if any(p in t for p in ["ya viaje", "ya viajé", "cliente", "viaje con ustedes", "compré", "compre"]):
        return "cliente"

    return "lead"

def convert_decimals(obj):
    if isinstance(obj, list): return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict): return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal): return int(obj) if obj % 1 == 0 else float(obj)
    return obj

def detectar_pais(texto):
    t = texto.lower()

    if any(p in t for p in ["argentina", "argentino", "arg"]):
        return "Argentina"

    if any(p in t for p in ["españa", "español", "espania", "espańa"]):
        return "España"

    return "No definido"

def extraer_telefono(texto):

    patron = r'(\+?\d[\d\s\-\(\)]{7,20}\d)'

    match = re.search(patron, texto)

    if match:
        return match.group(1)

    return None

def normalizar_extracciones(extracted, user_question):
    texto = user_question.lower().strip()

    # Teléfonos
    telefono = extraer_telefono(user_question)
    if telefono:
        extracted["phone_contact"] = telefono

    # Números escritos en texto
    numeros_texto = {
        "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10
    }

    if not extracted.get("people"):
        # Número exacto como mensaje
        if texto in numeros_texto:
            extracted["people"] = numeros_texto[texto]
        elif texto.isdigit():
            extracted["people"] = int(texto)
        else:
            # Número dentro de una frase: "somos 3", "viajamos 4 personas", etc.
            match = re.search(r'\b(\d+)\b', texto)
            if match:
                num = int(match.group(1))
                # Evitar confundir años o presupuestos con personas
                if 1 <= num <= 20:
                    extracted["people"] = num

    return extracted

def calcular_estado_presupuesto(destination, people, budget):

    if not destination or not people or not budget:
        return None

    try:

        print(f"Destino recibido: {destination}")
        print(f"Personas recibidas: {people}")
        print(f"Budget recibido: {budget}")

        destino = str(destination).lower().strip()

        budget_clean = re.sub(
            r"[^\d]",
            "",
            str(budget)
        )

        presupuesto_total = float(budget_clean)

        viajeros = int(people)

        MIN_BUDGETS = {
            "china": 5000,
            "japon": 6000,
            "japón": 6000,
            "egipto": 3500,
            "turquia": 4000,
            "turquía": 4000,
            "grecia": 4000,
            "españa": 4500,
            "espana": 4500,
            "italia": 4500
        }

        minimo_persona = MIN_BUDGETS.get(destino)

        if not minimo_persona:
            return None

        minimo_total = minimo_persona * viajeros

        print(f"Presupuesto limpio: {presupuesto_total}")
        print(f"Minimo requerido: {minimo_total}")

        if presupuesto_total < minimo_total:
            return "low"

        elif presupuesto_total < minimo_total * 1.3:
            return "adjusted"

        else:
            return "good"

    except Exception as e:
        print(f"ERROR PRESUPUESTO: {e}")
        return None
    

def formatear_historial(history, assistant_name="Asistente"):
    if not history:
        return "No hay historial previo."

    texto = f"--- CONVERSACIÓN CON IA {assistant_name.upper()} ---\n"

    for msg in history:
        u = msg.get('user', 'Usuario')
        a = msg.get('assistant', assistant_name)

        texto += f"Cliente: {u}\n"
        texto += f"Asistente: {a}\n"
        texto += "----------------\n"

    return texto