from django.db import models

FORMAT_DIGITAL = "digital"
FORMAT_PRINT = "print"
FORMAT_CHOICES = [
    (FORMAT_DIGITAL, "Digital: a PDF to enjoy anywhere"),
    (FORMAT_PRINT, "Print + Digital: hardcover book, gift box and PDF"),
]


class Tag(models.Model):
    """Occasion tags (Travel, Wedding...) filter cover styles.
    People tags (Family, Friends...) describe who the book is about."""

    OCCASION = "occasion"
    PEOPLE = "people"
    KIND_CHOICES = [
        (OCCASION, "Occasion"),
        (PEOPLE, "People"),
    ]

    name = models.CharField(max_length=40, unique=True)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name


class CoverStyle(models.Model):
    """A memory-book design that customers choose from. This is the main product catalogue."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    subtitle = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    colour = models.CharField(
        max_length=7,
        help_text="Hex colour for the cover preview, e.g. #173e35",
    )
    occasion = models.ForeignKey(
        Tag,
        on_delete=models.PROTECT,
        related_name="cover_styles",
        limit_choices_to={"kind": Tag.OCCASION},
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PackageTier(models.Model):
    """Photo-count packages. The price depends on the tier and on digital vs print."""

    name = models.CharField(max_length=40, unique=True)
    min_photos = models.PositiveSmallIntegerField()
    max_photos = models.PositiveSmallIntegerField()
    digital_price = models.DecimalField(max_digits=7, decimal_places=2)
    print_price = models.DecimalField(max_digits=7, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["min_photos"]

    def __str__(self):
        return f"{self.name} ({self.min_photos}–{self.max_photos} photos)"


class GiftBox(models.Model):
    """Physical stock for print orders: one row per style and colour combination."""

    STYLE_CHOICES = [
        ("classic", "Classic Ribbon"),
        ("botanical", "Botanical Notes"),
        ("starlit", "Starlit Moments"),
        ("vintage", "Vintage Letter"),
    ]
    COLOUR_CHOICES = [
        ("green", "Forest Green"),
        ("blue", "Dusty Blue"),
        ("cream", "Warm Cream"),
        ("rose", "Dusty Rose"),
    ]

    style = models.CharField(max_length=20, choices=STYLE_CHOICES)
    colour = models.CharField(max_length=20, choices=COLOUR_CHOICES)
    stock = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)

    class Meta:
        ordering = ["style", "colour"]
        constraints = [
            models.UniqueConstraint(
                fields=["style", "colour"],
                name="unique_giftbox_style_colour",
            ),
        ]

    @property
    def is_low_stock(self):
        return self.stock <= self.reorder_level

    def __str__(self):
        return f"{self.get_style_display()} / {self.get_colour_display()}"