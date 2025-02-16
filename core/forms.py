# ordenadores/forms.py
from django import forms

class ChatbotForm(forms.Form):
    user_query = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Escribe aqui qué ordenador quieres...'})
    )
