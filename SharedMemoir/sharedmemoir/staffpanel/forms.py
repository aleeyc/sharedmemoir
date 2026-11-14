from django import forms
from django.core.validators import FileExtensionValidator, RegexValidator
from django.utils.text import slugify

from accounts.forms import BootstrapFormMixin
from shop.models import CoverStyle, PackageTier

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

class CoverStyleForm(BootstrapFormMixin, forms.ModelForm):
    colour = forms.CharField(
        max_length=7,
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Choose a colour.")],
        widget=forms.TextInput(attrs={"type": "color"}),
        help_text="The colour of this cover in the shop's previews.",
    )

    class Meta:
        model = CoverStyle
        fields = ["name", "slug", "subtitle", "description", "colour", "occasion", "is_active"]
        labels = {"is_active": "Show this cover style in the shop"}
        help_texts = {"slug": "Used in the web address, e.g. /configure/wanderlust/. Leave blank to create it from the name."}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        # Bootstrap's special class for colour pickers
        self.fields["colour"].widget.attrs["class"] = "form-control form-control-color"

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("slug") and cleaned.get("name"):
            cleaned["slug"] = slugify(cleaned["name"])  # "Our Vows" -> "our-vows"
        return cleaned


class PackageTierForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PackageTier
        fields = ["name", "min_photos", "max_photos", "digital_price", "print_price", "is_active"]
        labels = {
            "digital_price": "Digital price (S$)",
            "print_price": "Print + Digital price (S$)",
            "is_active": "Offer this package to customers",
        }

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_photos"), cleaned.get("max_photos")
        if low is not None and high is not None:
            if low < 1:
                self.add_error("min_photos", "A package needs at least 1 photo.")
            if high < low:
                self.add_error("max_photos", "The maximum must be at least the minimum.")

        digital, printed = cleaned.get("digital_price"), cleaned.get("print_price")
        if digital is not None and digital <= 0:
            self.add_error("digital_price", "The price must be more than S$0.")
        if digital is not None and printed is not None and printed < digital:
            self.add_error("print_price", "Print + Digital can't cost less than Digital only.")
        return cleaned


class StockAdjustForm(forms.Form):
    change = forms.IntegerField(min_value=-500, max_value=500, initial=0)
    reorder_level = forms.IntegerField(min_value=0, max_value=500)