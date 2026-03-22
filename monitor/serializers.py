from rest_framework import serializers
from .models import Keyword, ContentItem, Flag


class KeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Keyword
        fields = ['id', 'name']

    def validate_name(self, value):
        
        return value.strip().lower()


class ContentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ContentItem
        fields = ['id', 'title', 'source', 'body', 'last_updated']


class FlagSerializer(serializers.ModelSerializer):
    
    keyword_name  = serializers.CharField(
        source='keyword.name',
        read_only=True
    )
    content_title = serializers.CharField(
        source='content_item.title',
        read_only=True
    )
    content_body  = serializers.CharField(
        source='content_item.body',
        read_only=True
    )

    class Meta:
        model  = Flag
        fields = [
            'id',
            'keyword_name',
            'content_title',
            'content_body',
            'score',
            'status',
            'reviewed_at',
        ]
        
        read_only_fields = ['score', 'reviewed_at']


class FlagStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Used only for PATCH /flags/{id}/
    Reviewer can ONLY change the status field — nothing else.
    """
    class Meta:
        model  = Flag
        fields = ['status']

    def validate_status(self, value):
        allowed = ['pending', 'relevant', 'irrelevant']
        if value not in allowed:
            raise serializers.ValidationError(
                f"Status must be one of: {allowed}"
            )
        return value