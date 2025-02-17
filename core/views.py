# ordenadores/views.py
from decimal import Decimal
from django.shortcuts import render
import os
from django.http import JsonResponse
from .forms import ChatbotForm
from django.contrib import messages
from .utils import chatbot_response, ensure_table_exists, extract_entities_from_pdf, insert_into_db

def inicio(request):
    return render(request, 'core/inicio.html')  # Página de carga de PDF

def upload_pdf(request):
    context = {}
    if request.method == "POST":
        
        if 'pdf' in request.FILES:
            pdf_file = request.FILES['pdf']
            
            # Asegurarse de que el directorio 'temp' existe
            temp_directory = 'temp'
            if not os.path.exists(temp_directory):
                os.makedirs(temp_directory)  # Crear el directorio 'temp' si no existe
            
            # Guardar el archivo temporalmente
            pdf_path = os.path.join(temp_directory, pdf_file.name)
            
            # Guardar el archivo
            with open(pdf_path, 'wb') as f:
                f.write(pdf_file.read())

            try:
                # 1️⃣ Verificar si la tabla existe
                ensure_table_exists()

                # 2️⃣ Extraer los datos del PDF
                extracted_data = extract_entities_from_pdf(pdf_path)
                context = {'extracted_data': extracted_data}
                print(context)
                # 3️⃣ Insertar los datos en la base de datos
                insert_into_db(extracted_data)

                # Si todo se ejecutó sin errores, agregar un mensaje de éxito
                messages.success(request, "PDF cargado con éxito.")
                
                

            except Exception as e:
                # Si ocurre algún error, agregar un mensaje de error
                messages.error(request, f"Hubo un error: {str(e)}")
        else:
            messages.error(request, "No se ha enviado un archivo PDF.")

    return render(request, 'core/upload_pdf.html' ,context)  # Página de carga de PDF


# app/views.py
  # Aquí debes colocar tu lógica de chatbot como una función

def chatbot(request):
    response = None
    if request.method == 'POST':
        form = ChatbotForm(request.POST)
        if form.is_valid():
            # Procesa la consulta y genera la respuesta del chatbot
            user_query = form.cleaned_data['user_query']
            #response = {'mensaje': 'This is what I have found for you:', 'Nada': False, 'laptops': [{'Marca': 'LG', 'Modelo': 'gram 17Z90R', 'Procesador': 'Intel', 'Tarjeta_grafica': 'RTX™ 3050 Ti', 'RAM': 'Si', 'Pulgadas': Decimal('17.00'), 'Precio': Decimal('2205.78')}, {'Marca': 'LG', 'Modelo': 'gram 17Z90R', 'Procesador': 'Intel', 'Tarjeta_grafica': 'RTX™ 3050 Ti', 'RAM': 'Si', 'Pulgadas': Decimal('17.00'), 'Precio': Decimal('2205.78')}]}
            response = chatbot_response(user_query)
            print(f"RESPUESTA: {response}")
    else:
        form = ChatbotForm()

    return render(request, 'core/chat.html', {'form': form, 'response': response})

