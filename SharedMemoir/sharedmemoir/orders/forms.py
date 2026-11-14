from django import forms

from accounts.forms import BootstrapFormMixin

from .models import Review


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


class ReviewForm(BootstrapFormMixin, forms.ModelForm):
    # Declared here so the radio buttons have no empty "---------" choice.
    rating = forms.TypedChoiceField(
        choices=Review.RATING_CHOICES, coerce=int, widget=forms.RadioSelect,
        label="Your rating", error_messages={"required": "Please choose a rating."},
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        labels = {"comment": "Your review (optional)"}
        widgets = {
            "comment": forms.Textarea(attrs={
                "rows": 4, "placeholder": "What did you love? What could we do better?",
            }),
        }
