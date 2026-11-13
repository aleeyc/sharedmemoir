from decimal import Decimal

from django.core.management.base import BaseCommand

from shop.models import CoverStyle, GiftBox, PackageTier, Tag

OCCASIONS = ["Travel", "Wedding", "Sports", "Celebrations", "Everyday"]
PEOPLE = ["Family", "Friends", "Classmates", "Colleagues"]

# name, slug, subtitle, colour, occasion
COVERS = [
    ("Wanderlust", "wanderlust", "Every road you took still counts", "#173e35", "Travel"),
    ("Our Vows", "our-vows", "Write your love into a book", "#697d87", "Wedding"),
    ("In Our Element", "in-our-element", "For every moment you gave it your all", "#42666c", "Sports"),
    ("Days to Celebrate", "days-to-celebrate", "The days we gathered, shining bright", "#7a504c", "Celebrations"),
    ("Everyday Letters", "everyday-letters", "Little joys in ordinary days", "#7c765e", "Everyday"),
]

# name, min photos, max photos, digital price, print price
TIERS = [
    ("A Moment", 1, 10, "12", "42"),
    ("Little Days", 11, 20, "22", "52"),
    ("Good Times", 21, 30, "32", "62"),
    ("Long Stories", 31, 40, "52", "82"),
    ("The Collection", 41, 50, "78", "108"),
]


class Command(BaseCommand):
    help = "Create or update the MEMORA catalogue: tags, cover styles, package tiers and gift-box stock."

    def handle(self, *args, **options):
        for name in OCCASIONS:
            Tag.objects.update_or_create(name=name, defaults={"kind": Tag.OCCASION})
        for name in PEOPLE:
            Tag.objects.update_or_create(name=name, defaults={"kind": Tag.PEOPLE})

        for name, slug, subtitle, colour, occasion in COVERS:
            CoverStyle.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "subtitle": subtitle,
                    "colour": colour,
                    "occasion": Tag.objects.get(name=occasion),
                },
            )

        for name, low, high, digital, printed in TIERS:
            PackageTier.objects.update_or_create(
                name=name,
                defaults={
                    "min_photos": low,
                    "max_photos": high,
                    "digital_price": Decimal(digital),
                    "print_price": Decimal(printed),
                },
            )

        for style, _label in GiftBox.STYLE_CHOICES:
            for colour, _label in GiftBox.COLOUR_CHOICES:
                GiftBox.objects.get_or_create(
                    style=style,
                    colour=colour,
                    defaults={"stock": 20},
                )

        self.stdout.write(self.style.SUCCESS("MEMORA catalogue seeded."))