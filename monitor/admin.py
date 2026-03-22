from django.contrib import admin
from .models import Keyword, ContentItem, Flag

admin.site.register(Keyword)
admin.site.register(ContentItem)
admin.site.register(Flag)