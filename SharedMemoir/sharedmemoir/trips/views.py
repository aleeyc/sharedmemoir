from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import TripForm


@login_required
def create_trip(request):
    if request.method == "POST":
        form = TripForm(request.POST)

        if form.is_valid():
            trip = form.save(commit=False)
            trip.created_by = request.user
            trip.save()

            messages.success(
                request,
                "Your trip has been created successfully!"
            )
            return redirect("home")
    else:
        form = TripForm()

    return render(
        request,
        "trips/create.html",
        {"form": form}
    )