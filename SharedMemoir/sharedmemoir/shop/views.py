from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .bag import BAG_SESSION_KEY, bag_initial, clear_bag, get_bag, save_bag
from .forms import ConfigureForm, StoryForm
from .models import FORMAT_DIGITAL, CoverStyle, PackageTier, Tag
from .recommender import recommend_tier

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

@login_required
def configure(request, slug):
    cover = get_object_or_404(CoverStyle, slug=slug, is_active=True)
    recommendation = None      # filled in when the ML model has recommended a package
    recommend_error = False

    if request.method == "POST" and "recommend" in request.POST:
        # The customer pressed "Recommend a package for me".
        # Keep everything they have typed so far, so nothing is lost when the page reloads.
        initial = request.POST.dict()
        initial["occasion_tags"] = request.POST.getlist("occasion_tags")
        initial["people_tags"] = request.POST.getlist("people_tags")

        # Only the four story answers are needed for a recommendation.
        story_form = StoryForm(request.POST)
        if story_form.is_valid():
            tier, photos = recommend_tier(story_form.cleaned_data)
            if tier:
                initial["tier"] = tier.id   # select the recommended package for the customer
                recommendation = {"tier": tier, "photos": photos}
        else:
            recommend_error = True
        form = ConfigureForm(initial=initial)

    elif request.method == "POST":
        form = ConfigureForm(request.POST)
        if form.is_valid():
            # Run the model on the final answers and keep its recommendation with the bag.
            tier, photos = recommend_tier(form.cleaned_data)
            save_bag(request, form.cleaned_data, tier, photos)
            messages.success(request, "Added to your bag.")
            return redirect("bag")
    else:
        stored = request.session.get(BAG_SESSION_KEY)
        if stored and request.GET.get("edit"):
            form = ConfigureForm(initial=bag_initial(stored))
            # Show again which package the model recommended for this bag.
            tier = PackageTier.objects.filter(pk=stored.get("recommended_tier_id")).first()
            if tier:
                recommendation = {"tier": tier, "photos": stored["predicted_photos"]}
        else:
            form = ConfigureForm(initial={"cover": cover.id, "format": FORMAT_DIGITAL})

    return render(request, "shop/configure.html", {
        "form": form,
        "cover": cover,
        "recommendation": recommendation,
        "recommend_error": recommend_error,
    })


def bag(request):
    return render(request, "shop/bag.html", {"bag": get_bag(request)})


@require_POST
def bag_remove(request):
    clear_bag(request)
    messages.info(request, "Your bag is now empty.")
    return redirect("bag")