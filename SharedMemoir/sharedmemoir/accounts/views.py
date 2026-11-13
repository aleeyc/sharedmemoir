from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, RegisterForm
from .models import CustomerProfile


def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to MEMORA, {user.profile.full_name}!")
        return redirect("home")

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    profile, _created = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.username, "age_group": "25-34"},
    )
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("profile")

    return render(request, "accounts/profile.html", {"form": form})