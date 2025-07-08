from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    # Contract templates
    path('templates/', views.ContractTemplateListView.as_view(), name='template_list'),
    path('templates/<int:pk>/', views.ContractTemplateDetailView.as_view(), name='template_detail'),
    path('templates/create/', views.ContractTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.ContractTemplateUpdateView.as_view(), name='template_edit'),
    
    # Contracts
    path('', views.ContractListView.as_view(), name='list'),
    path('<uuid:contract_id>/', views.ContractDetailView.as_view(), name='detail'),
    path('booking/<int:booking_pk>/template/<int:template_pk>/create/', 
         views.ContractCreateView.as_view(), name='create'),
    
    # Contract actions
    path('<uuid:contract_id>/sign/', views.contract_sign_view, name='sign'),
    path('<uuid:contract_id>/send/', views.send_contract_for_signature, name='send'),
    path('<uuid:contract_id>/cancel/', views.cancel_contract, name='cancel'),
    
    # File downloads
    path('<uuid:contract_id>/download/', views.download_contract_pdf, name='download'),
    path('<uuid:contract_id>/download/signed/', 
         views.download_contract_pdf, {'signed': True}, name='download_signed'),
    
    # Bulk operations
    path('bulk-create/', views.bulk_create_contracts, name='bulk_create'),
    
    # Dashboard
    path('dashboard/', views.ContractDashboardView.as_view(), name='dashboard'),
    
    # AJAX endpoints
    path('api/statistics/', views.contract_statistics, name='statistics'),
    path('<uuid:contract_id>/api/reminder/', views.create_contract_reminder, name='create_reminder'),
]