from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from .models import User, Task, Document, MediaItem, ChatRoom, Message
from .forms import RegisterForm, TaskForm, DocumentForm, MediaItemForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'core/login.html')

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'core/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    tasks_total = Task.objects.filter(assigned_to=request.user).count()
    tasks_done = Task.objects.filter(assigned_to=request.user, status='done').count()
    tasks_pending = tasks_total - tasks_done
    
    recent_tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')[:5]
    recent_docs = Document.objects.filter(uploaded_by=request.user).order_by('-created_at')[:5]
    recent_media = MediaItem.objects.filter(uploaded_by=request.user).order_by('-created_at')[:5]
    
    context = {
        'tasks_total': tasks_total,
        'tasks_done': tasks_done,
        'tasks_pending': tasks_pending,
        'recent_tasks': recent_tasks,
        'recent_docs': recent_docs,
        'recent_media': recent_media,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def kanban_board(request):
    tasks = {
        'todo': Task.objects.filter(assigned_to=request.user, status='todo'),
        'in_progress': Task.objects.filter(assigned_to=request.user, status='in_progress'),
        'review': Task.objects.filter(assigned_to=request.user, status='review'),
        'done': Task.objects.filter(assigned_to=request.user, status='done'),
    }
    return render(request, 'core/tasks/kanban.html', {'tasks': tasks})

@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    return render(request, 'core/tasks/task_detail.html', {'task': task})

@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            messages.success(request, 'Задача создана!')
            return redirect('kanban')
    else:
        form = TaskForm()
    
    return render(request, 'core/tasks/task_form.html', {'form': form, 'title': 'Создать задачу'})

@login_required
def task_edit(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Задача обновлена!')
            return redirect('task_detail', task_id=task.id)
    else:
        form = TaskForm(instance=task)
    
    return render(request, 'core/tasks/task_form.html', {'form': form, 'title': 'Редактировать задачу'})

@login_required
def task_change_status(request, task_id, status):
    task = get_object_or_404(Task, id=task_id)
    if status in dict(Task.STATUS_CHOICES):
        task.status = status
        task.save()
        messages.success(request, f'Статус задачи "{task.title}" изменён!')
    return redirect('kanban')

@login_required
def document_list(request):
    documents = Document.objects.filter(uploaded_by=request.user).order_by('-created_at')
    return render(request, 'core/documents/document_list.html', {'documents': documents})

@login_required
def document_upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, 'Документ загружен!')
            return redirect('document_list')
    else:
        form = DocumentForm()
    
    return render(request, 'core/documents/document_form.html', {'form': form, 'title': 'Загрузить документ'})

@login_required
def document_detail(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    return render(request, 'core/documents/document_detail.html', {'doc': doc})

@login_required
def media_list(request):
    media_items = MediaItem.objects.filter(uploaded_by=request.user).order_by('-created_at')
    return render(request, 'core/media/media_list.html', {'media_items': media_items})

@login_required
def media_upload(request):
    if request.method == 'POST':
        form = MediaItemForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.uploaded_by = request.user
            media.save()
            messages.success(request, 'Файл загружен в медиатеку!')
            return redirect('media_list')
    else:
        form = MediaItemForm()
    
    return render(request, 'core/media/media_upload.html', {'form': form})

# Функции для чата
@login_required
def chat_list(request):
    user = request.user
    private_chats = ChatRoom.objects.filter(
        room_type='private'
    ).filter(
        models.Q(participant1=user) | models.Q(participant2=user)
    )
    
    chats_with_info = []
    for chat in private_chats:
        last_message = Message.objects.filter(room=chat).order_by('-created_at').first()
        other_user = chat.get_other_user(user)
        unread_count = Message.objects.filter(room=chat, is_read=False).exclude(sender=user).count()
        
        chats_with_info.append({
            'chat': chat,
            'last_message': last_message,
            'other_user': other_user,
            'unread_count': unread_count,
        })
    
    chats_with_info.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else '', reverse=True)
    users = User.objects.exclude(id=user.id)
    
    context = {
        'private_chats': chats_with_info,
        'users': users,
    }
    return render(request, 'core/chat/chat_list.html', context)

@login_required
def chat_room(request, room_name='general'):
    user = request.user
    
    if room_name != 'general':
        try:
            room = ChatRoom.objects.get(name=room_name)
            if user not in [room.participant1, room.participant2]:
                return redirect('chat_list')
        except ChatRoom.DoesNotExist:
            return redirect('chat_list')
    
    room, created = ChatRoom.objects.get_or_create(
        name=room_name,
        defaults={'room_type': 'general' if room_name == 'general' else 'private'}
    )
    
    messages_list = Message.objects.filter(room=room).order_by('created_at')[:100]
    
    context = {
        'messages': messages_list,
        'room': room,
        'room_name': room_name,
    }
    return render(request, 'core/chat/chat_room.html', context)

@login_required
def create_private_chat(request, user_id):
    current_user = request.user
    other_user = get_object_or_404(User, id=user_id)
    
    room_name = f"private_{min(current_user.id, other_user.id)}_{max(current_user.id, other_user.id)}"
    
    room, created = ChatRoom.objects.get_or_create(
        name=room_name,
        defaults={
            'room_type': 'private',
            'participant1': current_user,
            'participant2': other_user
        }
    )
    
    return redirect('chat_room', room_name=room_name)

from django.http import JsonResponse

@login_required
def media_add_reaction(request, media_id):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        reaction = data.get('reaction')
        
        media = get_object_or_404(MediaItem, id=media_id)
        
        # Инициализируем структуру реакций если её нет
        if not media.reactions:
            media.reactions = {'user_reactions': {}}
        if 'user_reactions' not in media.reactions:
            media.reactions['user_reactions'] = {}
        
        # Добавляем или убираем реакцию
        user_id = str(request.user.id)
        if media.reactions['user_reactions'].get(user_id) == reaction:
            # Убираем реакцию
            del media.reactions['user_reactions'][user_id]
        else:
            # Добавляем реакцию
            media.reactions['user_reactions'][user_id] = reaction
        
        media.save()
        
        # Подсчитываем количество каждой реакции
        reaction_counts = {}
        for r in dict(MediaItem.REACTION_CHOICES).keys():
            reaction_counts[r] = list(media.reactions['user_reactions'].values()).count(r)
        
        return JsonResponse({
            'success': True,
            'reactions': reaction_counts,
            'user_reaction': media.reactions['user_reactions'].get(user_id)
        })
    
    return JsonResponse({'success': False})