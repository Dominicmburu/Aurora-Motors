from rest_framework import serializers
from .models import (
    ContractTemplate, Contract, ContractSignature, ContractAnalytics
)

class ContractTemplateSerializer(serializers.ModelSerializer):
    contract_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ContractTemplate
        fields = [
            'id', 'name', 'template_type', 'version', 'is_active',
            'is_required', 'requires_signature', 'contract_count'
        ]

class ContractListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    booking_number = serializers.CharField(source='booking.booking_number', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Contract
        fields = [
            'contract_id', 'title', 'status', 'user_name', 'template_name',
            'booking_number', 'sent_date', 'signed_date', 'expires_at',
            'days_until_expiry', 'created_at'
        ]

class ContractDetailSerializer(ContractListSerializer):
    signature_count = serializers.SerializerMethodField()
    can_be_signed = serializers.BooleanField(read_only=True)
    
    class Meta(ContractListSerializer.Meta):
        fields = ContractListSerializer.Meta.fields + [
            'content', 'signature_count', 'can_be_signed', 'notes'
        ]
    
    def get_signature_count(self, obj):
        return obj.signatures.count()

class ContractSignatureSerializer(serializers.ModelSerializer):
    signer_name = serializers.CharField(source='signer.get_full_name', read_only=True)
    
    class Meta:
        model = ContractSignature
        fields = [
            'id', 'signature_type', 'signer_name', 'signature_date'
        ]

class ContractAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractAnalytics
        fields = [
            'view_count', 'unique_viewers', 'first_viewed', 'last_viewed',
            'time_to_sign', 'sign_attempts', 'download_count'
        ]