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


MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB


class MultipleFileInput(forms.ClearableFileInput):
    """A file input that lets the customer select several files at once."""
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """Checks every selected file is a real image and returns them as a list.
    (This is the pattern from the Django documentation on uploading multiple files.)"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*", "multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(file, initial) for file in data]
        return [single_file_clean(data, initial)]


class PhotoUploadForm(BootstrapFormMixin, forms.Form):
    images = MultipleImageField(
        label="Choose photos",
        help_text="JPG or PNG, up to 10 MB each. You can select several photos at once.",
    )

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order

    def clean_images(self):
        images = self.cleaned_data["images"]
        if not images:
            raise forms.ValidationError("Choose at least one photo.")

        for image in images:
            if image.size > MAX_PHOTO_SIZE:
                raise forms.ValidationError(f"{image.name} is larger than 10 MB.")

        # The package decides the maximum number of photos.
        tier = self.order.tier
        space_left = tier.max_photos - self.order.photos.count()
        if len(images) > space_left:
            raise forms.ValidationError(
                f"Your {tier.name} package holds up to {tier.max_photos} photos. "
                f"You can add {space_left} more."
            )
        return images

class RevisionRequestForm(BootstrapFormMixin, forms.Form):
    details = forms.CharField(
        min_length=10, max_length=1000,
        label="What would you like us to change?",
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "e.g. Please use the beach photo on the cover and move the group photo to page 2.",
        }),
    )