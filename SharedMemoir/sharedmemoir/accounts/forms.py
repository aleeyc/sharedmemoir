from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import CustomerProfile


class BootstrapFormMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=100)
    age_group = forms.ChoiceField(choices=CustomerProfile.AGE_GROUPS)

    field_order = ["username", "email", "full_name", "age_group", "password1", "password2"]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.save()
        CustomerProfile.objects.create(
            user=user,
            full_name=self.cleaned_data["full_name"],
            age_group=self.cleaned_data["age_group"],
        )
        return user


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ["full_name", "phone", "age_group", "address_line", "postal_code"]

    def clean_postal_code(self):
        code = self.cleaned_data["postal_code"].strip()
        if code and not (code.isdigit() and len(code) == 6):
            raise forms.ValidationError("Enter a 6-digit Singapore postal code.")
        return code