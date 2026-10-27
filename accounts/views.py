from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, RegisterForm

DEMO_ACCOUNTS = [
    ("customer1", "Customer", "Shop, book service, track your car", "bi-person", "ico-blue"),
    ("sales1", "Sales executive", "Test drives, trade-ins, sales", "bi-briefcase", "ico-green"),
    ("mech1", "Mechanic", "Job queue and parts used", "bi-wrench-adjustable", "ico-amber"),
    ("admin", "Admin", "Analytics, stock and everything else", "bi-shield-lock", "ico-red"),
]


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    extra_context = {"demo_accounts": DEMO_ACCOUNTS}


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to CarCraft, {user.first_name}!")
        return redirect("dashboard:home")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
