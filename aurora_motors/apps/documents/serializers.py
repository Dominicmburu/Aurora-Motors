from rest_framework import serializers
from .models import (
    Document, DocumentCategory, DocumentShare, DocumentVersion
)

class DocumentCategorySerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(read_only=True)
    max_file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentCategory
        fields = [
            'id', 'name', 'description', 'is_required', 'allowed_extensions',
            'max_file_size', 'max_file_size_mb', 'document_count'
        ]
    
    def get_max_file_size_mb(self, obj):
        if obj.max_file_size:
            return round(obj.max_file_size / (1024 * 1024), 1)
        return None

class DocumentListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    file_size_display = serializers.CharField(source='formatted_file_size', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'name', 'document_type', 'category_name', 'user_name',
            'status', 'is_verified', 'file_size_display', 'expiry_date',
            'is_expired', 'days_until_expiry', 'created_at'
        ]

class DocumentDetailSerializer(DocumentListSerializer):
    file_extension = serializers.CharField(read_only=True)
    version_count = serializers.SerializerMethodField()
    
    class Meta(DocumentListSerializer.Meta):
        fields = DocumentListSerializer.Meta.fields + [
            'description', 'issue_date', 'issuing_authority', 'document_number',
            'file_extension', 'original_filename', 'version_count', 'review_notes'
        ]
    
    def get_version_count(self, obj):
        return obj.versions.count()

class DocumentShareSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source='document.name', read_only=True)
    shared_with_name = serializers.CharField(source='shared_with.get_full_name', read_only=True)
    shared_by_name = serializers.CharField(source='shared_by.get_full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DocumentShare
        fields = [
            'id', 'document_name', 'shared_with_name', 'shared_by_name',
            'access_type', 'expires_at', 'is_expired', 'access_count',
            'last_accessed', 'created_at'
        ]

class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentVersion
        fields = [
            'id', 'version_number', 'uploaded_by_name', 'change_notes', 'created_at'
        ]