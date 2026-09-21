from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "file", "status", "extracted_text", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "extracted_text", "created_at", "updated_at"]
