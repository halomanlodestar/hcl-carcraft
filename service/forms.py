import re

from django import forms
from django.utils import timezone

from inventory.forms import grouped_model_choices
from inventory.models import VehicleModel

from .models import CustomerVehicle

PAINT_CHOICES = [
    ("#f5f5f4", "White"), ("#111827", "Black"), ("#9ca3af", "Silver"), ("#4b5563", "Grey"),
    ("#b91c1c", "Red"), ("#1d4ed8", "Blue"), ("#065f46", "Green"), ("#92400e", "Brown"),
]


class CustomerVehicleForm(forms.ModelForm):
    vehicle_model = forms.ChoiceField(label="Make & model")
    year = forms.TypedChoiceField(coerce=int)
    color_hex = forms.ChoiceField(choices=PAINT_CHOICES, widget=forms.RadioSelect, initial="#f5f5f4", label="Colour")

    class Meta:
        model = CustomerVehicle
        fields = ["vehicle_model", "year", "reg_number", "km_driven", "color_hex"]
        labels = {"reg_number": "Registration number", "km_driven": "Odometer (km)"}
        widgets = {"reg_number": forms.TextInput(attrs={"placeholder": "MH12AB1234", "class": "text-uppercase"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle_model"].choices = grouped_model_choices()
        y = timezone.now().year
        self.fields["year"].choices = [(i, i) for i in range(y, y - 20, -1)]

    def clean_vehicle_model(self):
        try:
            return VehicleModel.objects.get(pk=self.cleaned_data["vehicle_model"])
        except (VehicleModel.DoesNotExist, ValueError):
            raise forms.ValidationError("Please choose your car.")

    def clean_reg_number(self):
        reg = re.sub(r"[\s-]", "", self.cleaned_data["reg_number"]).upper()
        if not re.fullmatch(r"[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}", reg):
            raise forms.ValidationError("Enter a valid registration number, e.g. MH12AB1234.")
        return reg
