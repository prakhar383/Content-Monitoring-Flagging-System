from django.contrib import admin
from .models import Keyword, ContentItem, Flag


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display  = ['id', 'name']
    search_fields = ['name']


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display  = ['id', 'title', 'source', 'last_updated']
    search_fields = ['title', 'source']


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display  = ['id', 'keyword', 'content_item', 'score', 'status', 'reviewed_at']
    list_filter   = ['status']
    search_fields = ['keyword__name', 'content_item__title']