from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("faq/", views.faq, name="faq"),
    path("configure/<slug:slug>/", views.configure, name="configure"),
    path("bag/", views.bag, name="bag"),
    path("bag/remove/", views.bag_remove, name="bag_remove"),
]