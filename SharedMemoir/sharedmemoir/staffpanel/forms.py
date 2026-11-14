from django import forms
from django.core.validators import FileExtensionValidator, RegexValidator

from accounts.forms import BootstrapFormMixin

MAX_PDF_BYTES = 50 * 1024 * 1024 #50 megabytes

COURIERS = [
    ("SingPost", "SingPost"),
    ("Ninja Van", "Ninja Van"),
    ("J&T Express", "J&T Express"),
    ("DHL Express", "DHL Express"),
]


class DeliverPdfForm(BootstrapFormMixin, forms.Form):
    pdf = forms.FileField(
        label="Memory-book PDF",
        validators=[FileExtensionValidator(["pdf"])],
        widget=forms.ClearableFileInput(attrs={"accept": "application/pdf"}),
    )
    note = forms.CharField(
        max_length=200, required=False, label="Note to the customer (optional)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Swapped the cover photo as requested"}),
    )

    def clean_pdf(self):
        pdf = self.cleaned_data["pdf"]
        if pdf.size > MAX_PDF_BYTES:
            raise forms.ValidationError("The PDF must be 50 MB or smaller.")
        header = pdf.read(5)
        pdf.seek(0)
        if not header.startswith(b"%PDF"):
            raise forms.ValidationError("This file is not a valid PDF.")
        return pdf


class ShipForm(BootstrapFormMixin, forms.Form):
    courier = forms.ChoiceField(choices=COURIERS)
    tracking_number = forms.CharField(
        max_length=30,
        validators=[RegexValidator(r"^[A-Za-z0-9-]{6,30}$",
                                   "Enter a valid tracking number: 6–30 letters, digits or dashes.")],
    )