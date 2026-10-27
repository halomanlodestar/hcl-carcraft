from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField()
    phone = forms.CharField(max_length=15, required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone"]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "city", "address"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
