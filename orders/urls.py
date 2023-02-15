from django.urls import path
from . import views

urlpatterns = [
    path('pubblic', views.pubblic_offert),
    path('total_offers', views.all_offers),
    path('gain', views.lose_gain),
    path('convert', views.fiat_bit),
    path('delete', views.delete_order)
]
