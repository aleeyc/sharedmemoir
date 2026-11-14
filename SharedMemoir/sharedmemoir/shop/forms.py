from django import forms
from accounts.forms import BootstrapFormMixin
from .models import FORMAT_CHOICES, FORMAT_PRINT, CoverStyle, GiftBox, PackageTier, Tag

class TierChoiceField(forms.ModelChoiceField):
    """Shows each package with its photo range and both prices."""

    def label_from_instance(self, tier):
        return (f"{tier.name} · {tier.min_photos}–{tier.max_photos} photos · "
                f"Digital S${tier.digital_price:.0f} / Print S${tier.print_price:.0f}")


class StoryForm(BootstrapFormMixin, forms.Form):
    """The four answers about the customer's story.
    These are exactly the inputs of the ML model (see shop/recommender.py)."""

    occasion_tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.filter(kind=Tag.OCCASION),
        widget=forms.CheckboxSelectMultiple, label="Occasion",
        error_messages={"required": "Choose at least one occasion."},
    )
    people_tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.filter(kind=Tag.PEOPLE),
        widget=forms.CheckboxSelectMultiple, label="People",
        error_messages={"required": "Choose at least one people tag."},
    )
    group_size = forms.IntegerField(min_value=1, max_value=50, label="How many people are in this story?")
    event_days = forms.IntegerField(min_value=1, max_value=60, label="How many days did it span?")


class ConfigureForm(StoryForm):
    """The whole customise page: the story answers above plus the fields below."""

    cover = forms.ModelChoiceField(
        queryset=CoverStyle.objects.filter(is_active=True),
        widget=forms.RadioSelect, empty_label=None, label="Cover style",
    )
    format = forms.ChoiceField(choices=FORMAT_CHOICES, widget=forms.RadioSelect, label="Format")
    tier = TierChoiceField(
        queryset=PackageTier.objects.filter(is_active=True),
        widget=forms.RadioSelect, empty_label=None, label="Photo package",
    )
    title = forms.CharField(
        max_length=80, label="Give your book a title",
        widget=forms.TextInput(attrs={"placeholder": "For example: Our Graduation Trip"}),
    )
    gift_box = forms.ModelChoiceField(
        queryset=GiftBox.objects.filter(stock__gt=0), required=False,
        label="Gift box (print orders only)", empty_label="Choose a gift box",
    )
    notes = forms.CharField(
        required=False, label="A note for the studio (optional)",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "A mood you love, or a message for someone special…"}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("format") == FORMAT_PRINT:
            if not cleaned.get("gift_box"):
                self.add_error("gift_box", "Choose a gift box for your printed book.")
        else:
            cleaned["gift_box"] = None
        return cleaned