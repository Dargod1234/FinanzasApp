from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('phone/', views.phone_auth, name='phone-auth'),
    path('phone/request-otp/', views.request_otp, name='request-otp'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', views.profile_view, name='profile'),
]
