from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegisterForm


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            # Save the new user into the database
            user = form.save()

            # Log the new user in straight away
            login(request, user)

            messages.success(
                request,
                "Welcome to SharedMemoir! Your account has been created."
            )
            return redirect("home")
    else:
        form = RegisterForm()

    return render(
        request,
        "registration/register.html",
        {"form": form}
    )
