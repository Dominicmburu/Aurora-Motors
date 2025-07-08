from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Document management
    path('', views.DocumentListView.as_view(), name='list'),
    path('<int:pk>/', views.DocumentDetailView.as_view(), name='detail'),
    path('upload/', views.DocumentUploadView.as_view(), name='upload'),
    path('<int:pk>/edit/', views.DocumentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.DocumentDeleteView.as_view(), name='delete'),
    
    # Document actions
    path('<int:pk>/download/', views.download_document, name='download'),
    path('<int:pk>/review/', views.review_document, name='review'),
    path('<int:pk>/share/', views.share_document, name='share'),
    path('<int:pk>/version/', views.upload_document_version, name='upload_version'),
    
    # Document categories
    path('categories/', views.DocumentCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.DocumentCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.DocumentCategoryUpdateView.as_view(), name='category_edit'),
    
    # Document templates
    path('templates/', views.DocumentTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.DocumentTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.DocumentTemplateUpdateView.as_view(), name='template_edit'),
    
    # Shared documents
    path('shared/', views.SharedDocumentsView.as_view(), name='shared'),
    
    # Bulk operations
    path('bulk-actions/', views.bulk_document_actions, name='bulk_actions'),
    
    # Dashboard
    path('dashboard/', views.DocumentDashboardView.as_view(), name='dashboard'),
    
    # AJAX endpoints
    path('api/statistics/', views.document_statistics, name='statistics'),
    path('api/check-requirements/', views.check_document_requirements, name='check_requirements'),
    path('api/validate-upload/', views.validate_document_upload, name='validate_upload'),
]