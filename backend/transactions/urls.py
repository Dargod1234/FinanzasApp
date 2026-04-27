from django.urls import path
from . import views

urlpatterns = [
    path('transactions/', views.transaction_list, name='transaction-list'),
    path('transactions/upload/', views.transaction_upload_image, name='transaction-upload-image'),
    path('transactions/parse-voice/', views.parse_voice_transaction, name='transaction-parse-voice'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction-detail'),
    path('transactions/<int:pk>/image/', views.transaction_image, name='transaction-image'),
    path('dashboard/summary/', views.dashboard_summary, name='dashboard-summary'),
    path('plan/status/', views.plan_status, name='plan-status'),
    path('categories/', views.category_list_create, name='category-list-create'),
    path('categories/<int:pk>/', views.category_delete, name='category-delete'),
    path('encrypted-transactions/', views.encrypted_transaction_list_create, name='encrypted-transaction-list-create'),
]
