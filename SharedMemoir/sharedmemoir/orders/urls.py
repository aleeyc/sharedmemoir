from django.urls import path

from . import views

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("orders/<int:pk>/success/", views.order_success, name="order_success"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<int:pk>/cancel/", views.cancel_order, name="cancel_order"),
    path("orders/<int:pk>/review/", views.review_order, name="review_order"),
    path("orders/<int:pk>/photos/", views.order_photos, name="order_photos"),
    path("orders/<int:pk>/photos/submit/", views.submit_photos, name="submit_photos"),
    path("orders/<int:pk>/photos/<int:photo_id>/caption/", views.save_caption, name="save_caption"),
    path("orders/<int:pk>/photos/<int:photo_id>/delete/", views.delete_photo, name="delete_photo"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/revision/", views.request_revision, name="request_revision"),
    path("orders/<int:pk>/approve/", views.approve_design, name="approve_design"),
    path("orders/<int:pk>/received/", views.confirm_receipt, name="confirm_receipt"),
]