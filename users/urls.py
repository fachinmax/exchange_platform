from django.urls import path
from . import views

urlpatterns = [
    path('login', views.sing_in),
    path('register', views.sing_up),
    path('logout', views.user_logout),
    path('top_up', views.top_up_account),
    path('users', views.get_users),
    path('users_account', views.get_user_account)
]
