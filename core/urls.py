from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('tasks/', views.kanban_board, name='kanban'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:task_id>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:task_id>/status/<str:status>/', views.task_change_status, name='task_change_status'),
    
    path('documents/', views.document_list, name='document_list'),
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<int:doc_id>/', views.document_detail, name='document_detail'),
    
    path('media/', views.media_list, name='media_list'),
    path('media/upload/', views.media_upload, name='media_upload'),
    
    # Чаты
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/<str:room_name>/', views.chat_room, name='chat_room'),
    path('chat/private/<int:user_id>/', views.create_private_chat, name='create_private_chat'),

    path('media/reaction/<int:media_id>/', views.media_add_reaction, name='media_add_reaction'),
]