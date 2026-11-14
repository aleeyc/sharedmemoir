from django import forms

from accounts.forms import BootstrapFormMixin


class CheckoutForm(BootstrapFormMixin, forms.Form):
    contact_name = forms.CharField(max_length=100, label="Name")
    contact_email = forms.EmailField(label="Email address")
    contact_phone = forms.CharField(max_length=20, label="Phone")
    shipping_address = forms.CharField(max_length=200, label="Shipping address")
    shipping_postal_code = forms.CharField(max_length=10, label="Postal code")
    agree = forms.BooleanField(
        label="I understand the package, photo limits and one-free-revision policy.",
        error_messages={"required": "Please confirm you have read the ordering terms."},
    )

    def __init__(self, *args, is_print=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not is_print:
            del self.fields["shipping_address"]
            del self.fields["shipping_postal_code"]

    def clean_shipping_postal_code(self):
        code = self.cleaned_data["shipping_postal_code"].strip()
        if not (code.isdigit() and len(code) == 6):
            raise forms.ValidationError("Enter a 6-digit Singapore postal code.")
        return code