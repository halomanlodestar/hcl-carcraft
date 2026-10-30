from django import forms
from django.utils import timezone

from accounts.models import User

from .models import Make, TradeInRequest, VehicleModel


def grouped_model_choices():
    groups = []
    for make in Make.objects.prefetch_related("models"):
        groups.append((make.name, [(m.pk, m.name) for m in make.models.all()]))
    return [("", "Select your car")] + groups


class TradeInForm(forms.Form):
    reg_number = forms.CharField(max_length=15, required=False, label="Registration number")
    vehicle_model = forms.ChoiceField(label="Make & model")
    year = forms.TypedChoiceField(coerce=int)
    km_driven = forms.IntegerField(label="Kilometres driven", min_value=0, max_value=500_000,
                                   widget=forms.NumberInput(attrs={"placeholder": "e.g. 45000", "step": 1000}))
    condition_rating = forms.ChoiceField(choices=TradeInRequest.ConditionRating.choices, widget=forms.RadioSelect,
                                         initial="GOOD", label="Overall condition")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle_model"].choices = grouped_model_choices()
        this_year = timezone.now().year
        self.fields["year"].choices = [(y, y) for y in range(this_year, this_year - 16, -1)]

    def clean_vehicle_model(self):
        try:
            return VehicleModel.objects.select_related("make").get(pk=self.cleaned_data["vehicle_model"])
        except (VehicleModel.DoesNotExist, ValueError):
            raise forms.ValidationError("Please choose your car.")

    def clean_reg_number(self):
        return self.cleaned_data["reg_number"].upper().replace(" ", "").replace("-", "")


class SaleForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=User.objects.none())
    sale_price = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    trade_in = forms.ModelChoiceField(queryset=TradeInRequest.objects.none(), required=False,
                                      empty_label="No trade-in", label="Apply trade-in")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = User.objects.filter(role=User.Role.CUSTOMER).order_by("first_name")
        self.fields["customer"].label_from_instance = lambda u: f"{u.display_name} · {u.phone or u.email}"
        self.fields["trade_in"].queryset = TradeInRequest.objects.filter(
            status=TradeInRequest.Status.OFFERED, sale__isnull=True
        ).select_related("customer", "vehicle_model__make")
        self.fields["trade_in"].label_from_instance = (
            lambda t: f"{t.customer.display_name}: {t.year} {t.vehicle_model} (₹{t.offered_value:,.0f})"
        )

    def clean(self):
        data = super().clean()
        trade_in, customer = data.get("trade_in"), data.get("customer")
        if trade_in and customer and trade_in.customer_id != customer.pk:
            self.add_error("trade_in", "This trade-in belongs to a different customer.")
        return data


class OfferForm(forms.Form):
    offered_value = forms.DecimalField(max_digits=12, decimal_places=2, min_value=1000)
