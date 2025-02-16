# ordenadores/utils.py
from decimal import Decimal, InvalidOperation
import pyodbc
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from project.settings import DOC_INT_ENDPOINT, DOC_INT_KEY, DOC_INT_MODEL, AI_ENDPOINT, AI_KEY, AI_MODEL, DATABASES


# Coloca tus funciones aquí, como extract_entities_from_pdf, insert_into_db, etc.
document_intelligence_endpoint = DOC_INT_ENDPOINT
document_intelligence_key = DOC_INT_KEY
document_intelligence_model_id = DOC_INT_MODEL  # ID del modelo personalizado

openai_endpoint = AI_ENDPOINT
openai_api_key = AI_KEY


client = AzureOpenAI(
        azure_endpoint=openai_endpoint,
        api_key=openai_api_key,
        api_version="2024-05-01-preview"
    )

server = DATABASES['default']['HOST']
database = DATABASES['default']['NAME']
username = DATABASES['default']['USER']
password = DATABASES['default']['PASSWORD']
driver = DATABASES['default']['OPTIONS']['driver']


def ensure_table_exists():
    conn = pyodbc.connect(f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}')
    cursor = conn.cursor()

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Ordenadores')
BEGIN
    CREATE TABLE Ordenadores (
        ID INT IDENTITY(1,1) PRIMARY KEY,
        Precio DECIMAL(10,2),  -- Cambio a número decimal con 2 decimales
        Marca NVARCHAR(100),
        Modelo NVARCHAR(100),
        Almacenamiento INT,  -- Cambio a entero
        Grafica NVARCHAR(100),
        Marca_grafica NVARCHAR(50),
        Procesador NVARCHAR(100),
        Marca_Procesador NVARCHAR(50),
        Resolucion NVARCHAR(50),
        Pulgadas DECIMAL(5,2),  -- Cambio a decimal para valores como 15.6
        Peso DECIMAL(10,2),
        Color NVARCHAR(50),
        Ram INT,  -- Cambio a entero
        WebCam NVARCHAR(10),
        SO NVARCHAR(50),
        Fecha_Registro DATETIME DEFAULT GETDATE()
    )
END
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ Verificación completada: La tabla 'Ordenadores' está lista.")

# =============================================================
# 2️⃣ Extraer entidades desde un PDF usando Azure Document Intelligence
# =============================================================
def extract_entities_from_pdf(pdf_path):
    client = DocumentIntelligenceClient(document_intelligence_endpoint, AzureKeyCredential(document_intelligence_key))

    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document(
            model_id=document_intelligence_model_id, 
            body=f.read()  # Pass the actual content as the body, not inside a dictionary
        )
        result = poller.result()
    
    extracted_data = []
    for document in result.documents:
        data = {
            "Precio": document.fields.get("Precio", {}).get("content", None),
            "Marca": document.fields.get("Marca", {}).get("content", None),
            "Modelo": document.fields.get("Modelo", {}).get("content", None),
            "Almacenamiento": document.fields.get("Almacenamiento", {}).get("content", None),
            "Grafica": document.fields.get("Grafica", {}).get("content", None),
            "Marca_grafica": document.fields.get("Marca_grafica", {}).get("content", None),
            "Procesador": document.fields.get("Procesador", {}).get("content", None),
            "Marca_Procesador": document.fields.get("Marca_procesador", {}).get("content", None),
            "Resolucion": document.fields.get("Resolucion", {}).get("content", None),
            "Pulgadas": document.fields.get("Pulgadas", {}).get("content", None),
            "Peso": document.fields.get("Peso", {}).get("content", None),
            "Color": document.fields.get("Color", {}).get("content", None),
            "Ram": document.fields.get("RAM", {}).get("content", None),
            "WebCam": document.fields.get("WebCam", {}).get("content", None),
            "SO": document.fields.get("SO", {}).get("content", None),
        }
        print(data)
        extracted_data.append(data)
    
    return extracted_data


def safe_convert(value, default=None):
    try:
        # Clean the value by removing non-numeric characters (e.g., currency symbols, commas)
        if value is None or value == '':
            return default  # Return default (None or 0) if value is empty or None
        
        # Remove commas (if any) and any non-numeric characters (you can customize this as needed)
        cleaned_value = value.replace(",", "")  # Remove commas for thousands separation
        
        # Convert to Decimal to handle the precision correctly
        decimal_value = Decimal(cleaned_value)

        # Format the decimal value to 2 decimal places with a comma as the decimal separator
        formatted_value = "{:,.2f}".format(decimal_value)  # Format the number with 2 decimals and thousands separators
        formatted_value = formatted_value.replace(",", "X").replace(".", ",").replace("X", ".")  # Replace dot with comma

        return formatted_value  # Return the formatted value as a string
    except (ValueError, TypeError, InvalidOperation):
        # If conversion fails, return the default value (None or empty string)
        return default
    
# =============================================================
# 3️⃣ Insertar los datos extraídos en la base de datos
# =============================================================
import re
from decimal import Decimal, InvalidOperation

def to_number(value):
    """Convierte un valor a número eliminando símbolos y espacios innecesarios."""
    if not value:
        return None
    # Primero, eliminamos cualquier símbolo que no sea numérico, excepto el punto o la coma.
    value = re.sub(r"[^\d,\.]", "", value)  # Quita todo lo que no sea número, coma o punto
    value = value.replace(".", "")
    print(value)
    # Si el valor tiene coma, la usamos como separador decimal (se usa el formato europeo).
    if "," in value:
        # Reemplazamos la coma por punto para el formato decimal (ej. 554,33 → 554.33)
        value = value.replace(",", ".")

    try:
        # Convertimos el valor a Decimal para asegurar una representación adecuada
        # Si es un número entero, se convertirá automáticamente
        return Decimal(value)
    except InvalidOperation:
        return None


def normalize_ram(value):
    """Extrae solo el número de la RAM en GB."""
    if not value:
        return None
    match = re.search(r"\d+", value)  # Busca solo números
    return int(match.group(0)) if match else None

def normalize_storage(value):
    """Convierte almacenamiento a número (GB o TB como GB)."""
    if not value:
        return None
    
    # Eliminamos los puntos como separadores de miles.
    value = value.replace(".", "")
    
    # Buscamos el número (puede haber más de uno si hay comas o puntos en el valor)
    match = re.search(r"(\d+)", value)  # Captura solo el número
    
    if match:
        num = int(match.group(0))  # Extraemos el número del valor.
        
        # Comprobamos si el valor tiene "TB" (o "tb"), y si es así, convertimos a GB.
        if "tb" in value.lower():
            num *= 1024  # Convertir TB a GB
        
        return num
    
    return None


def normalize_processor(value):
    """
    Extrae solo la parte esencial del nombre del procesador.
    Ejemplo: "Ryzen 7 7730U" -> "Ryzen 7", "Intel Core i7-13800H" -> "i7"
    """
    if not value:
        return None

    value = value.lower()  # Convertir a minúsculas para evitar problemas de formato

    # Buscar "Ryzen X" o "iX" donde X es un número (ej: Ryzen 7, i7)
    match = re.search(r"(ryzen\s\d+|i\d+)", value, re.IGNORECASE)

    if match:
        return match.group(0).capitalize()  # Capitaliza la primera letra por consistencia

    return value  # Si no se encuentra un formato conocido, se devuelve el valor original


def insert_into_db(data):
    conn = pyodbc.connect(f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}')
    cursor = conn.cursor()

    for item in data:
        item["Precio"] = to_number(item["Precio"])  # This converts it to Decimal (no formatting yet)
        item["Ram"] = normalize_ram(item["Ram"])
        item["Almacenamiento"] = normalize_storage(item["Almacenamiento"])
        item["Pulgadas"] = to_number(item["Pulgadas"])
        item["Procesador"] = normalize_processor(item["Procesador"])
        item["Peso"] = to_number(item["Peso"])

        # Insert the raw Decimal (not formatted string) into the DB
        cursor.execute("""
            INSERT INTO Ordenadores (Precio, Marca, Modelo, Almacenamiento, Grafica, Marca_grafica, Procesador, Marca_Procesador, Resolucion, Pulgadas, Peso, Color, Ram, WebCam, SO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, 
        item["Precio"], item["Marca"], item["Modelo"], item["Almacenamiento"], item["Grafica"], 
        item["Marca_grafica"], item["Procesador"], item["Marca_Procesador"], item["Resolucion"], 
        item["Pulgadas"], item["Peso"], item["Color"], item["Ram"], item["WebCam"], item["SO"])

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Datos insertados correctamente en la base de datos con el formato correcto.")


# =============================================================
# 4️⃣ Consultar la base de datos con OpenAI para el chatbot
# =============================================================
def extract_numeric_value(value):
    """Extrae el valor numérico de un string con texto adicional (como '32GB')"""
    return int(re.sub(r"[^\d]", "", value))

def gpt_parse_query(query):
    # Corrige errores ortográficos en la consulta del usuario
    response = client.chat.completions.create(
    model=AI_MODEL,
    messages=[
        {"role": "system", "content": """
            Be aware that the user might make spelling errors or use terms incorrectly. If so, correct the word in the query.
            However, be very careful not to confuse similar terms, especially those related to computer hardware:
            - 'RAM' refers to memory (e.g., 16GB of RAM).
            - 'Storage' refers to disk space (e.g., 256GB SSD or HDD).
            Usually, when 'GB' is mentioned without the word 'RAM', it refers to **Storage** (disk space).
            Do not confuse 'RAM' with 'Storage' or any other hardware component.
            Always ensure that 'RAM' and 'Storage' are kept distinct in their context. If unsure about the context, avoid making changes and leave the word as is.
            Limit yourself to only correcting misspelled words, nothing more."""},
        {"role": "user", "content": query}
    ]
)


    query = response.choices[0].message.content.strip()
    print(f"Corrected query: {query}")

    # Extraer información relevante (RAM, procesador, etc.)
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": """
            Extract only the relevant information (RAM, processor, brand, model...) from the user's question.
            - If the user specifies a numeric value (e.g., 16GB, 512GB), also determine if they mentioned a comparison condition (more than, at least, less than, etc.).
            - Use the following format for numeric values with comparisons:
            - 'Almacenamiento: > 512' (for 'more than 512GB')
            - 'RAM: >= 16' (for 'at least 16GB')
            - 'Pulgadas: < 15' (for 'less than 15 inches')
            - 'Almacenamiento: <= 50' (for '50GB or less')
            - Do not perform transformations on the 'Almacenamiento', if it comes as tb, put tb, if it comas as gb, put gb...
            - If no comparison condition is found, assume exact match.
            - Extract only the fields mentioned by the user.
            - The following fields should be extracted if present: Precio, Marca, Modelo, Almacenamiento, Grafica, Marca_grafica, Procesador, Marca_Procesador, Resolucion, Pulgadas, Peso, Color, RAM, WebCam, SO.
            - Be especially careful with RAM and Storage queries. If 'GB' appears without 'RAM', assume it refers to storage.
            - If at least **one field contains specific information, return only those fields**.
            - If **no field contains specific data**, return **only** the text: 'No info' (once, without listing all fields).
            - Example mappings:
            - 'A laptop with less than 512GB' → 'Almacenamiento: < 512'
            - 'I want a computer with at least 8GB of RAM' → 'RAM: >= 8'
            - 'A screen bigger than 14 inches' → 'Pulgadas: > 14'
            - 'The laptop with the most RAM' → 'No info'
            - 'The cheapest laptop' → 'No info'
            - 'I want a laptop with an i7 processor' → 'Procesador: i7'
            - 'I want a laptop with an Intel processor' → 'Marca_Procesador: Intel'
            - Return only the extracted information in this format, nothing else.
            """},
            {"role": "user", "content": query }
        ]
    )
    
    parsed_data = response.choices[0].message.content.strip()
    print(f"Extracted data: {parsed_data}")

    parsed_dict = {}

    # Si no se extrajeron entidades, identificar la intención
    if parsed_data == "No info":
        print("NADA")
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": """Determine the intent of the user's query based on the following categories:  
                - 'Barato': When the user is looking for cheap laptops, the cheapest options available.  
                - 'Caro': When the user is looking for expensive laptops, the most expensive options available.  
                - 'CPRatio': When the user is looking for a laptop with the best price-to-performance ratio.  
                - 'MasGB': When the user is looking for a laptop with a large amount of storage.  
                - 'MenosGB': When the user is looking for a laptop with minimal storage.  
                - 'MaxRAM': When the user is looking for a laptop with the highest possible RAM.  
                - 'MinRAM': When the user is looking for a laptop with the lowest possible RAM.  
                - 'Todos': When the user is looking for all available laptops.  
                - 'MaxPantalla': When the user is looking for laptops with the largest screen available.  
                - 'MinPantalla': When the user is looking for laptops with the smallest screen available.  
                Return only the intent name, nothing else."""},
                {"role": "user", "content": query}
            ]
)

        
        intent = response.choices[0].message.content.strip()
        parsed_dict["Intent"] = intent
        print(f"Detected intent: {intent}")
    else:
        # Función para convertir unidades de almacenamiento a GB
        def convert_to_gb(value):
            value_lower = value.lower()
            numeric_value = float(re.sub(r"[^\d.]", "", value))  # Extraer solo números

            if "tera" in value_lower or "tb" in value_lower or "teras" in value_lower:
                return numeric_value * 1024  # Convertir TB a GB
            elif "mega" in value_lower or "mb" in value_lower or "megas" in value_lower:
                return numeric_value / 1024  # Convertir MB a GB
            elif "kilo" in value_lower or "kb" in value_lower or "kilos" in value_lower:
                return numeric_value / 1048576  # Convertir KB a GB
            return numeric_value  # Asumir GB si no se especifica otra unidad

        # Procesar los datos extraídos
        for item in parsed_data.split("\n"):
            key_value = item.split(":")
            if len(key_value) == 2:
                key = key_value[0].strip()
                value = key_value[1].strip()
                print(f"Processing: {key} -> {value}")

                operator = parse_comparison_operator(value)  # Extraer operador si existe
                if key in ["Precio", "RAM", "Pulgadas", "Almacenamiento"]:
                    numeric_value = convert_to_gb(value) if key == "Almacenamiento" else extract_numeric_value(value)
                    parsed_dict[key] = {"value": numeric_value, "operator": operator}
                else:
                    parsed_dict[key] = {"value": value, "operator": None}

    print(f"Final parsed data: {parsed_dict}")
    return parsed_dict


import string

def parse_comparison_operator(value):
    """Interpreta los operadores de comparación (mayor que, menor que, igual a)"""
    # Limpiamos el texto para evitar errores por espacios extra y eliminamos puntuación
    print(f"Analizando: '{value}'")  # Imprime el valor para depuración
    
    # Busca los operadores comunes
    if "o más" in value or "o mas" in value or "por lo menos" in value or ">=" in value:  # Nuevo caso para detectar "o más"
        print("Operador encontrado: '>='")
        return ">="  # Mayor o igual que
    elif "o menos" in value or "<=" in value:  # Nuevo caso para detectar "o menos"
        print("Operador encontrado: '<='")
        return "<="  # Menor o igual que
    elif "mayor que" in value or "más" in value or "mas" in value  or "+" in value or "<" in value:
        return "<"
    elif "menor que" in value or "menos" in value or "-" in value or ">" in value:
        return ">"
    else:
        # Si no hay operador, se asume que el valor es exacto
        return "="

# =============================================================
# 4️⃣ Construir la query
# =============================================================
def get_laptop_recommendations(parsed_query):
    # Conectarse a la base de datos
    conn = pyodbc.connect(f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}')
    cursor = conn.cursor()

    print(parsed_query)

    # Verificar si hay una intención en parsed_query
    if "Intent" in parsed_query:
        intent = parsed_query["Intent"]

        intent_queries = {
            "Barato": "SELECT TOP 3 * FROM Ordenadores ORDER BY Precio ASC",
            "Caro": "SELECT TOP 3 * FROM Ordenadores ORDER BY Precio DESC",
            "CPRatio": "SELECT TOP 3 * FROM Ordenadores ORDER BY Ram DESC, Precio ASC",
            "MasGB": "SELECT TOP 3 * FROM Ordenadores ORDER BY Almacenamiento DESC",
            "MenosGB": "SELECT TOP 3 * FROM Ordenadores ORDER BY Almacenamiento ASC",
            "MaxRAM": "SELECT TOP 3 * FROM Ordenadores ORDER BY Ram DESC",
            "MinRAM": "SELECT TOP 3 * FROM Ordenadores ORDER BY Ram ASC",
            "Todos": "SELECT * FROM Ordenadores",
            "MaxPantalla": "SELECT TOP 3 * FROM Ordenadores ORDER BY Pulgadas DESC",
            "MinPantalla": "SELECT TOP 3 * FROM Ordenadores ORDER BY Pulgadas ASC"
        }

        if intent in intent_queries:
            sql_query = intent_queries[intent]
            print(f"Executing Intent Query: {sql_query}")
            cursor.execute(sql_query)
            results = cursor.fetchall()
            conn.close()
            return results  # Devuelve los resultados directamente

    else:
        # Si no hay "Intent", se ejecuta la consulta con filtros dinámicos
        conditions = []
        params = []

        # Filtrar por RAM
        if "RAM" in parsed_query:
            ram_data = parsed_query["RAM"]
            conditions.append(f"Ram {ram_data['operator']} ?")
            params.append(ram_data["value"])

        # Filtrar por procesador
        if "Procesador" in parsed_query:
            conditions.append("Procesador LIKE ?")
            params.append(parsed_query["Procesador"]["value"])
        if "Marca_Procesador" in parsed_query:
            conditions.append("Marca_Procesador LIKE ?")
            params.append(parsed_query["Marca_Procesador"]["value"])

        # Filtrar por marca
        if "Marca" in parsed_query:
            conditions.append("Marca LIKE ?")
            params.append(parsed_query["Marca"]["value"])

        # Filtrar por modelo
        if "Modelo" in parsed_query:
            conditions.append("Modelo LIKE ?")
            params.append(parsed_query["Modelo"]["value"])

        # Filtrar por almacenamiento
        if "Almacenamiento" in parsed_query:
            storage_data = parsed_query["Almacenamiento"]
            conditions.append(f"Almacenamiento {storage_data['operator']} ?")
            params.append(storage_data["value"])

        # Filtrar por gráfica
        if "Grafica" in parsed_query:
            conditions.append("Grafica LIKE ?")
            params.append(parsed_query["Grafica"]["value"])

        # Filtrar por sistema operativo
        if "SO" in parsed_query:
            conditions.append("SO LIKE ?")
            params.append(parsed_query["SO"]["value"])

        # Filtrar por tamaño de pantalla
        if "Pulgadas" in parsed_query:
            pulgadas_data = parsed_query["Pulgadas"]
            conditions.append(f"Pulgadas {pulgadas_data['operator']} ?")
            params.append(pulgadas_data["value"])

        # Filtrar por marca de gráfica
        if "Marca_grafica" in parsed_query:
            conditions.append("Marca_grafica LIKE ?")
            params.append(parsed_query["Marca_grafica"]["value"])

        # Filtrar por resolución
        if "Resolucion" in parsed_query:
            conditions.append("Resolucion LIKE ?")
            params.append(parsed_query["Resolucion"]["value"])

        # Filtrar por peso
        if "Peso" in parsed_query:
            conditions.append("Peso LIKE ?")
            params.append(parsed_query["Peso"]["value"])

        # Filtrar por color
        if "Color" in parsed_query:
            conditions.append("Color LIKE ?")
            params.append(parsed_query["Color"]["value"])

        # Filtrar por WebCam
        if "WebCam" in parsed_query:
            conditions.append("WebCam LIKE ?")
            params.append(parsed_query["WebCam"]["value"])

        # Filtrar por precio
        if "Precio" in parsed_query:
            price_data = parsed_query["Precio"]
            conditions.append(f"Precio {price_data['operator']} ?")
            params.append(price_data["value"])

        # Si no hay condiciones, devolver un mensaje indicando que no se ha encontrado una consulta válida
        if not conditions:
            return "No valid criteria found in the query."

        # Construcción dinámica de la consulta
        sql_query = f"SELECT * FROM Ordenadores WHERE {' AND '.join(conditions)}"

        # Reemplazar los parámetros
        final_query = sql_query
        for param in params:
            if isinstance(param, (int, float)):  # Si es número, sin comillas
                final_query = final_query.replace('?', str(param), 1)
            else:
                final_query = final_query.replace('?', f"'{param}'", 1)  # Si es string, con comillas

        print(f"Final SQL Query: {final_query}")
        cursor.execute(sql_query, params)
        results = cursor.fetchall()
        
        conn.close()
        return results
 
 # =============================================================
# 4️⃣ devolver los registros
# =============================================================
def detectar_idioma_gpt(texto):
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": f"Detect the language of this text, retrieve only the abreviation of it (for example: en, es, fr...), nothing more: {texto}"}]
    )
    return response.choices[0].message.content

def gpt_translate(text, target_language):

    translated_text = text

    if target_language != 'es':
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": f"Translate the following text to {target_language}."},
                {"role": "user", "content": text}
            ]
        )

        translated_text = response.choices[0].message.content.strip()
    return translated_text


# utils.py

# utils.py

def process_laptop_results(results):
    """
    Procesa los resultados de las recomendaciones de laptops y devuelve una lista de diccionarios.
    Cada diccionario contiene los detalles de una laptop.
    """
    laptop_list = []
    
    for r in results:
        laptop_info = {
            "Marca": r[2],  # Marca
            "Modelo": r[3],  # Modelo
            "Procesador": r[6],  # Procesador
            "Tarjeta_grafica": r[5],  # Tarjeta gráfica
            "RAM": r[13],  # RAM en GB
            "Almacenamiento": r[4],  # RAM en GB
            "Pulgadas": r[10],  # Tamaño de pantalla
            "Precio": r[1],  # Precio
        }
        laptop_list.append(laptop_info)
    
    return laptop_list


def chatbot_response(user_query):
    parsed_query = gpt_parse_query(user_query)  # Extrae especificaciones
    results = get_laptop_recommendations(parsed_query)  # Devuelve una lista de tuplas
    
    # Detectar el idioma de la consulta
    idioma = detectar_idioma_gpt(user_query)
    print("Idioma detectado:", idioma)

    # Crear el encabezado del mensaje
    header = "Esto es lo que he encontrado para ti:"
    
    # Traducir solo el encabezado
    translated_header = gpt_translate(header, idioma)

    if results:
        # Procesar los resultados de laptops
        laptops = process_laptop_results(results)

        # Crear una lista con diccionarios para cada laptop (con los campos claves)
        laptop_cards = []
        for laptop in laptops:
            laptop_cards.append({
                "Marca": laptop['Marca'],
                "Modelo": laptop['Modelo'],
                "Procesador": laptop['Procesador'],
                "Tarjeta_grafica": laptop['Tarjeta_grafica'],
                "RAM": laptop['RAM'],
                "Almacenamiento": laptop['Almacenamiento'],
                "Pulgadas": laptop['Pulgadas'],
                "Precio": laptop['Precio']
            })

        return {"mensaje": translated_header, "Nada": False, "laptops": laptop_cards}
    else:
        # Si no hay resultados, generar el mensaje adecuado
        response_text = "No encontré ningún equipo con esas características."
        
        # Traducir el mensaje si es necesario
        translated_response = gpt_translate(response_text, idioma)

        return {"mensaje": translated_response, "Nada": True, "laptops": []}
