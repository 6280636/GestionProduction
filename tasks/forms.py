from django.forms import ModelForm
from .models import Defect
from django import forms
from django.utils.translation import gettext as _



class EmployeeLoginForm(forms.Form):
    """
    Formulaire de connexion utilisant uniquement le numéro d'employé.
    """
    employee_number = forms.IntegerField(        
        widget=forms.NumberInput(attrs={
            'autofocus': 'autofocus',
            'onfocus': "this.value='';",
            'class': 'form-control',
            'placeholder': _('Entrez votre numéro de employé')
        })
    )

class DefectForm(forms.ModelForm):
    """
    Formulaire basé sur le modèle Defect pour gérer la création et la modification des défauts.
    """
    class Meta:
        model = Defect
        fields = ['unit_number', 'defect_type', 'part_number', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
