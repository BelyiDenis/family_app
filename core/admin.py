from django.contrib import admin
from .models import User, Family, Task, Document, MediaItem, ChatRoom, Message

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ['name', 'invite_code', 'created_at', 'created_by']
    search_fields = ['name', 'invite_code']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'family', 'is_active']
    list_filter = ['role', 'family']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'assigned_to', 'status', 'deadline', 'priority']
    list_filter = ['status', 'priority']
    search_fields = ['title']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'uploaded_by', 'created_at']
    list_filter = ['category']
    search_fields = ['title']

@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'uploaded_by', 'created_at']
    list_filter = ['type']