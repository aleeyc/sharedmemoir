"""Create demo customers, a studio account and orders at every stage of the MEMORA workflow.

    python manage.py seed_demo           # first time use
    python manage.py seed_demo --reset   # delete the demo orders and create them again

All demo accounts use the password in DEMO_PASSWORD. The photos and PDFs are
simple placeholder images drawn with Pillow.
"""
import io
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from accounts.models import CustomerProfile
from orders.models import Order, Review
from shop.models import FORMAT_DIGITAL, FORMAT_PRINT, CoverStyle, GiftBox, PackageTier, Tag
from shop.recommender import recommend_tier

DEMO_PASSWORD = "Memora2026!"
STAFF_USERNAME = "studio"

# username, full name, email, phone, age group, address, postal code, active/inactive
CUSTOMERS = [
    ("alice", "Alice Tan", "alice@example.com", "91234567", "25-34", "10 Tanjong Pagar Road #05-01", "088443", True),
    ("ben", "Ben Lim", "ben@example.com", "92345678", "35-44", "221 Bishan Street 23 #08-12", "570221", True),
    ("chloe", "Chloe Ng", "chloe@example.com", "93456789", "18-24", "5 Kent Ridge Drive", "119224", True),
    ("dev", "Dev Raj", "dev@example.com", "94567890", "45-54", "38 Jurong West Street 41 #11-03", "640038", True),
    ("emma", "Emma Wong", "emma@example.com", "95678901", "25-34", "1 Marina Boulevard #20-01", "018989", True),
    ("frank", "Frank Ho", "frank@example.com", "96789012", "55+", "", "", False),  # a deactivated account
]

S = Order.Status
D, P = FORMAT_DIGITAL, FORMAT_PRINT

# title, customer, cover slug, package, format, status, occasions, people, group size, days,
# gift box (style, colour) for print orders, days ago, used the free revision/didnt, review
ORDERS = [
    ("Our Kyoto Autumn", "alice", "wanderlust", "Good Times", P, S.COMPLETED, ["Travel"], ["Friends"], 4, 7,
     ("classic", "green"), 40, False, (5, "Absolutely beautiful. The studio picked the perfect photo for the cover.")),
    ("Mum & Dad's 30th", "ben", "days-to-celebrate", "Long Stories", P, S.COMPLETED, ["Celebrations"], ["Family"], 12, 1,
     ("botanical", "rose"), 35, True, (4, "Lovely gift. One revision fixed the page order exactly as we asked.")),
    ("Sec School Reunion", "chloe", "everyday-letters", "Little Days", D, S.COMPLETED, ["Everyday"], ["Classmates"], 15, 1,
     None, 30, False, (5, "Quick, easy and the PDF looks great on my phone.")),
    ("Bali with the Team", "dev", "wanderlust", "Long Stories", D, S.COMPLETED, ["Travel"], ["Colleagues"], 8, 4,
     None, 28, False, (2, "Nice design but it took longer than I expected.")),
    ("Christmas Party", "ben", "days-to-celebrate", "Good Times", D, S.COMPLETED, ["Celebrations"], ["Colleagues"], 20, 1,
     None, 25, False, (5, "Our whole office loved it!")),
    ("Weekend in Melaka", "chloe", "wanderlust", "A Moment", D, S.COMPLETED, ["Travel"], ["Friends"], 2, 2,
     None, 18, False, None),
    ("Our Wedding Day", "emma", "our-vows", "The Collection", P, S.SHIPPED, ["Wedding"], ["Family", "Friends"], 40, 1,
     ("starlit", "cream"), 14, False, None),
    ("Hokkaido Snow Trip", "alice", "wanderlust", "Good Times", P, S.PRINTING, ["Travel"], ["Friends"], 3, 9,
     ("vintage", "blue"), 10, False, None),
    ("Marathon Weekend", "ben", "in-our-element", "Little Days", D, S.DELIVERED, ["Sports"], ["Friends"], 6, 2,
     None, 8, False, None),
    ("Grandma's 80th", "chloe", "days-to-celebrate", "Good Times", P, S.REVISION, ["Celebrations"], ["Family"], 18, 1,
     ("classic", "rose"), 7, True, None),
    ("Dragon Boat Season", "dev", "in-our-element", "Long Stories", D, S.DELIVERED, ["Sports"], ["Colleagues"], 22, 3,
     None, 6, True, None),
    ("Penang Food Trail", "emma", "wanderlust", "Little Days", D, S.PRODUCING, ["Travel"], ["Friends"], 3, 3,
     None, 5, False, None),
    ("Baby's First Year", "alice", "everyday-letters", "The Collection", P, S.PRODUCING, ["Everyday"], ["Family"], 3, 60,
     ("botanical", "green"), 4, False, None),
    ("Office Retreat", "ben", "wanderlust", "Good Times", D, S.SUBMITTED, ["Travel"], ["Colleagues"], 10, 2,
     None, 2, False, None),
    ("Graduation Day", "chloe", "days-to-celebrate", "Little Days", P, S.SUBMITTED, ["Celebrations"], ["Classmates"], 6, 1,
     ("starlit", "blue"), 2, False, None),
    ("Family Staycation", "dev", "everyday-letters", "Little Days", D, S.WAITING, ["Everyday"], ["Family"], 4, 3,
     None, 1, False, None),
    ("Netball Finals", "emma", "in-our-element", "Little Days", P, S.WAITING, ["Sports"], ["Classmates"], 9, 1,
     ("classic", "blue"), 1, False, None),
    ("Bangkok Shopping", "alice", "wanderlust", "A Moment", P, S.CANCELLED, ["Travel"], ["Friends"], 2, 4,
     ("vintage", "rose"), 20, False, None),
]

COURIERS = ["SingPost", "Ninja Van", "J&T Express", "DHL Express"]
PHOTO_COLOURS = ["#5b7f95", "#7a9e7e", "#c98b6b", "#8c7aa9", "#d1a85b", "#5f8f8b"]
CAPTIONS = [
    "The view that made us stop and stare.", "Everyone finally in one photo!", "Our favourite meal of the trip.",
    "The moment we all burst out laughing.", "Golden hour, right before we left.", "", "",
]


def font(size):
    """Pillow's built-in font at the given size (older Pillow versions only have one size)."""
    try:
        return ImageFont.load_default(size=size)
    except (TypeError, ImportError, OSError):
        return ImageFont.load_default()


def shade(hex_colour, factor):
    """Make a colour darker, e.g. shade('#5b7f95', 0.7)."""
    red, green, blue = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return (int(red * factor), int(green * factor), int(blue * factor))


def make_photo(colour, label, filename):
    """A simple landscape placeholder photo as a JPEG."""
    image = Image.new("RGB", (800, 600), colour)
    draw = ImageDraw.Draw(image)
    draw.ellipse((560, 80, 700, 220), fill="#f4d58d")
    draw.polygon([(0, 600), (260, 320), (540, 600)], fill=shade(colour, 0.75))
    draw.polygon([(300, 600), (600, 360), (800, 500), (800, 600)], fill=shade(colour, 0.6))
    draw.text((30, 30), label, fill="white", font=font(28))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=70)
    return ContentFile(buffer.getvalue(), name=filename)


def make_pdf(order, version):
    """A two-page placeholder memory book: a cover page and one inside page."""
    cover = Image.new("RGB", (1240, 1754), order.cover.colour)  # A4 at 150 dpi
    draw = ImageDraw.Draw(cover)
    draw.text((120, 1250), order.title, fill="white", font=font(80))
    draw.text((120, 1370), f"{order.cover.name} - MEMORA", fill="white", font=font(40))
    draw.text((120, 1430), f"Version {version}", fill="white", font=font(32))

    inside = Image.new("RGB", (1240, 1754), "#f7f5ed")
    draw = ImageDraw.Draw(inside)
    draw.text((120, 140), order.title, fill="#173e35", font=font(56))
    draw.text((120, 230), "Demo page: the studio's layout of your photos and stories goes here.",
              fill="#6e7972", font=font(30))
    for row in range(2):
        for col in range(2):
            left, top = 120 + col * 520, 340 + row * 640
            draw.rectangle((left, top, left + 480, top + 560), fill=PHOTO_COLOURS[(row * 2 + col) % len(PHOTO_COLOURS)])

    buffer = io.BytesIO()
    cover.save(buffer, "PDF", save_all=True, append_images=[inside], resolution=150)
    return ContentFile(buffer.getvalue(), name="memory-book.pdf")


def build_history(order, customer, studio, revised, photo_count):
    """The timeline steps (message, who did it) that lead to the order's current status."""
    status = order.status
    steps = [("Order placed and demo payment completed.", customer)]
    if status == S.CANCELLED:
        return steps + [("Order cancelled by the customer. Full refund issued (demo).", customer)]
    if status == S.WAITING:
        return steps

    steps.append((f"Customer submitted {photo_count} photos. Production can begin.", customer))
    if status == S.SUBMITTED:
        return steps
    steps.append(("Studio started designing the memory book.", studio))
    if status == S.PRODUCING:
        return steps

    steps.append(("Studio delivered the first version of the PDF.", studio))
    if revised:
        steps.append(("Customer requested their free revision.", customer))
        if status == S.REVISION:
            return steps
        steps.append(("Studio delivered the revised version (v2) of the PDF.", studio))
    if status == S.DELIVERED:
        return steps

    steps.append(("Customer approved the final design.", customer))
    if order.is_print:
        if status == S.PRINTING:
            return steps
        steps.append((f"Shipped with {order.courier}, tracking number {order.tracking_number}.", studio))
        if status == S.SHIPPED:
            return steps
        steps.append(("Customer confirmed the book arrived.", customer))
    return steps


class Command(BaseCommand):
    help = "Create demo customers, a studio account and orders at every stage of the workflow."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Delete the demo orders (and reset gift-box stock to 20) before creating them again.")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2108) 
        call_command("seed_catalogue")

        usernames = [row[0] for row in CUSTOMERS]
        existing = Order.objects.filter(customer__username__in=usernames)
        if existing.exists():
            if not options["reset"]:
                self.stdout.write(self.style.WARNING(
                    "Demo orders already exist. Run 'python manage.py seed_demo --reset' to recreate them."))
                return
            existing.delete()
            GiftBox.objects.update(stock=20)

        studio = self.create_staff()
        customers = {row[0]: self.create_customer(row) for row in CUSTOMERS}
        for row in ORDERS:
            self.create_order(row, customers, studio)

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(ORDERS)} demo orders for {len(CUSTOMERS)} customers. "
            f"Log in as '{STAFF_USERNAME}' or any customer (e.g. 'alice') with password {DEMO_PASSWORD}"))

    def create_staff(self):
        studio, _ = User.objects.get_or_create(username=STAFF_USERNAME, defaults={"email": "studio@memora.example"})
        studio.is_staff = True
        studio.set_password(DEMO_PASSWORD) 
        studio.save()
        return studio

    def create_customer(self, row):
        username, full_name, email, phone, age_group, address, postal_code, active = row
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.is_active = active
        user.set_password(DEMO_PASSWORD)
        user.save()
        CustomerProfile.objects.update_or_create(user=user, defaults={
            "full_name": full_name, "phone": phone, "age_group": age_group,
            "address_line": address, "postal_code": postal_code,
        })
        return user

    def create_order(self, row, customers, studio):
        (title, username, cover_slug, tier_name, fmt, status, occasions, people,
         group_size, days, box_key, days_ago, revised, review) = row
        customer = customers[username]
        profile = customer.profile
        cover = CoverStyle.objects.get(slug=cover_slug)
        tier = PackageTier.objects.get(name=tier_name)
        occasion_tags = Tag.objects.filter(name__in=occasions)
        people_tags = Tag.objects.filter(name__in=people)
        gift_box = GiftBox.objects.get(style=box_key[0], colour=box_key[1]) if box_key else None
        is_print = fmt == P

        # Ask the ML model what it would have recommended, like the configurator does
        recommended, predicted = recommend_tier({
            "occasion_tags": occasion_tags, "people_tags": people_tags,
            "group_size": group_size, "event_days": days,
        })

        placed_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(1, 8))
        shipped = is_print and status in (S.SHIPPED, S.COMPLETED)
        order = Order.objects.create(
            customer=customer, cover=cover, tier=tier, format=fmt, gift_box=gift_box,
            title=title, notes="", group_size=group_size, event_days=days,
            predicted_photos=predicted, recommended_tier=recommended,
            amount=tier.print_price if is_print else tier.digital_price,
            status=status, paid_at=placed_at,
            revision_used=revised,
            revision_request="Please put the group photo on the cover and move the sunset to the last page."
                             if revised else "",
            contact_name=profile.full_name, contact_email=customer.email, contact_phone=profile.phone,
            shipping_address=profile.address_line if is_print else "",
            shipping_postal_code=profile.postal_code if is_print else "",
            courier=random.choice(COURIERS) if shipped else "",
            tracking_number=f"SG{random.randint(100000000, 999999999)}" if shipped else "",
        )
        order.occasion_tags.set(occasion_tags)
        order.people_tags.set(people_tags)
        Order.objects.filter(pk=order.pk).update(created_at=placed_at)

        # Each print order that wasnt cancelled has uses one gift box
        if is_print and status != S.CANCELLED:
            GiftBox.objects.filter(pk=gift_box.pk).update(stock=F("stock") - 1)

        if status == S.CANCELLED:
            photo_count = 0
        elif status == S.WAITING:
            photo_count = tier.min_photos // 2
        else:
            photo_count = random.randint(tier.min_photos, min(tier.max_photos, tier.min_photos + 6))
        for number in range(1, photo_count + 1):
            order.photos.create(
                caption=random.choice(CAPTIONS),
                image=make_photo(random.choice(PHOTO_COLOURS), f"{title} - photo {number}", f"demo-photo-{number}.jpg"),
            )

        # Timeline spread out between the order date and now
        steps = build_history(order, customer, studio, revised, photo_count)
        gap = (timezone.now() - placed_at) / (len(steps) + 1)
        version = 0
        for index, (message, actor) in enumerate(steps):
            when = placed_at + gap * index
            event = order.add_event(message, actor=actor)
            type(event).objects.filter(pk=event.pk).update(created_at=when)
            if message.startswith("Studio delivered"):
                version += 1
                book = order.versions.create(number=version, pdf=make_pdf(order, version),
                                             note="Updated as requested." if version > 1 else "",
                                             uploaded_by=studio)
                type(book).objects.filter(pk=book.pk).update(created_at=when)

        if review:
            Review.objects.create(order=order, rating=review[0], comment=review[1])
