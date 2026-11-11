from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    # UserCreationForm already has username, password1 and password2.
    # We only add an email field on top of it.
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Give every input the Bootstrap "form-control" class
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
