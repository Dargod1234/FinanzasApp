from django.urls import path
from . import views

urlpatterns = [
    path('transactions/', views.transaction_list, name='transaction-list'),
    path('encrypted-transactions/', views.encrypted_transaction_list_create, name='encrypted-transaction-list-create'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction-detail'),
    path('transactions/<int:pk>/image/', views.transaction_image, name='transaction-image'),
    path('dashboard/summary/', views.dashboard_summary, name='dashboard-summary'),
]
