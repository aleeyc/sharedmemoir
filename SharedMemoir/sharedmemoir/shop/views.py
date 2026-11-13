from django.shortcuts import render

from .models import CoverStyle, PackageTier, Tag

HOW_IT_WORKS_STEPS = [
    ("Choose & customise", "Pick a cover style, a photo package, digital or print, and tag the occasion and people in your story."),
    ("Review & pay", "Check your order in the bag and complete a secure demo payment. No real money is charged."),
    ("Upload & create", "Upload your photos from your order page. Once your package's photo count is met, submit them to our studio."),
    ("PDF delivery", "Our studio designs your book and delivers it as a PDF you can read online or download."),
    ("Revisions", "Every order includes one free revision. Tell us what to change and we'll send an updated PDF."),
    ("Print & ship", "Print orders are printed, packed in your chosen gift box and shipped with a tracking number."),
]

FAQS = [
    ("How does pricing work?",
     "The price depends on your photo package and on whether you choose digital only or print + digital. "
     "Tags, cover styles and gift-box options are included at no extra cost."),
    ("Can I order before uploading my photos?",
     "Yes. You upload photos from your order page after checkout. Production starts once you submit "
     "a photo count within your package's range."),
    ("Can I select multiple tags? Do they cost extra?",
     "You can choose several occasion and people tags. They help our studio, and our recommendation model, "
     "understand your story. They never add to the price."),
    ("How does the free revision work?",
     "After we deliver your PDF, you may request one free revision before approving the final design. "
     "Earlier versions are kept on your order page."),
    ("How long does production take? Can I cancel?",
     "You can cancel for a full refund while your order is still awaiting photos. Once you submit photos, "
     "production begins and the order can no longer be cancelled."),
    ("How will I receive my digital memory book?",
     "Your PDF appears on your order page, where you can read it in the browser or download it."),
    ("Is this an automatically generated AI book?",
     "No. Our studio designs every book by hand. We use a machine-learning model only to recommend "
     "the photo package that best suits your occasion and group."),
]


def home(request):
    covers = CoverStyle.objects.filter(is_active=True).select_related("occasion")
    return render(request, "home.html", {"covers": covers})


def shop(request):
    covers = CoverStyle.objects.filter(is_active=True).select_related("occasion")
    selected_occasion = request.GET.get("occasion", "")
    if selected_occasion:
        covers = covers.filter(occasion__name=selected_occasion)

    return render(request, "shop/shop.html", {
        "covers": covers,
        "occasions": Tag.objects.filter(kind=Tag.OCCASION),
        "selected_occasion": selected_occasion,
        "tiers": PackageTier.objects.filter(is_active=True),
    })


def how_it_works(request):
    return render(request, "shop/how_it_works.html", {"steps": HOW_IT_WORKS_STEPS})


def faq(request):
    return render(request, "shop/faq.html", {"faqs": FAQS})