from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from django.utils import timezone
import json

from .models import User, Family, Task, Document, MediaItem, ChatRoom, Message
from .forms import RegisterForm, TaskForm, DocumentForm, MediaItemForm, CreateFamilyForm, JoinFamilyForm


def login_view(request):
    """Страница входа в систему"""
    if request.user.is_authenticated:
        # Если пользователь уже вошёл, перенаправляем
        if request.user.family:
            return redirect('dashboard')
        return redirect('family_setup')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.family:
                return redirect('dashboard')
            else:
                return redirect('family_setup')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'core/login.html')


def register_view(request):
    """Страница регистрации нового пользователя"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}! Теперь создайте или присоединитесь к семье.')
            return redirect('family_setup')
    else:
        form = RegisterForm()
    
    return render(request, 'core/register.html', {'form': form})


def logout_view(request):
    """Выход из системы"""
    logout(request)
    return redirect('login')


@login_required
def family_setup(request):
    """Страница создания или присоединения к семье"""
    if request.user.family:
        return redirect('dashboard')
    
    create_form = CreateFamilyForm()
    join_form = JoinFamilyForm()
    
    if request.method == 'POST':
        if 'create_family' in request.POST:
            create_form = CreateFamilyForm(request.POST)
            if create_form.is_valid():
                family_name = create_form.cleaned_data['family_name']
                family = Family.objects.create(
                    name=family_name,
                    created_by=request.user
                )
                request.user.family = family
                request.user.save()
                
                # Создаём общий чат для семьи
                ChatRoom.objects.create(
                    name=f"general_{family.id}",
                    room_type='general',
                    family=family
                )
                
                messages.success(request, f'Семья "{family_name}" создана! Код приглашения: {family.invite_code}')
                return redirect('dashboard')
        
        elif 'join_family' in request.POST:
            join_form = JoinFamilyForm(request.POST)
            if join_form.is_valid():
                invite_code = join_form.cleaned_data['invite_code'].upper()
                try:
                    family = Family.objects.get(invite_code=invite_code)
                    request.user.family = family
                    request.user.save()
                    messages.success(request, f'Вы присоединились к семье "{family.name}"!')
                    return redirect('dashboard')
                except Family.DoesNotExist:
                    messages.error(request, 'Неверный код приглашения')
    
    context = {
        'create_form': create_form,
        'join_form': join_form,
    }
    return render(request, 'core/family_setup.html', context)


@login_required
def family_invite(request):
    """Страница с кодом приглашения"""
    if not request.user.family:
        return redirect('family_setup')
    
    if request.method == 'POST':
        # Сгенерировать новый код
        family = request.user.family
        family.invite_code = None
        family.save()
        messages.success(request, f'Новый код приглашения: {family.invite_code}')
    
    return render(request, 'core/family_invite.html', {'family': request.user.family})


@login_required
def dashboard(request):
    """Главная страница с дашбордом"""
    if not request.user.family:
        return redirect('family_setup')
    
    family = request.user.family
    
    tasks_total = Task.objects.filter(family=family, assigned_to=request.user).count()
    tasks_done = Task.objects.filter(family=family, assigned_to=request.user, status='done').count()
    
    recent_tasks = Task.objects.filter(family=family, assigned_to=request.user).order_by('-created_at')[:5]
    recent_docs = Document.objects.filter(family=family, uploaded_by=request.user).order_by('-created_at')[:5]
    recent_media = MediaItem.objects.filter(family=family, uploaded_by=request.user).order_by('-created_at')[:5]
    
    context = {
        'tasks_total': tasks_total,
        'tasks_done': tasks_done,
        'tasks_pending': tasks_total - tasks_done,
        'recent_tasks': recent_tasks,
        'recent_docs': recent_docs,
        'recent_media': recent_media,
    }
    return render(request, 'core/dashboard.html', context)


# ==================== ЗАДАЧИ ====================

@login_required
def kanban_board(request):
    """Kanban-доска с задачами"""
    if not request.user.family:
        return redirect('family_setup')
    
    family = request.user.family
    
    tasks = {
        'todo': Task.objects.filter(family=family, assigned_to=request.user, status='todo'),
        'in_progress': Task.objects.filter(family=family, assigned_to=request.user, status='in_progress'),
        'review': Task.objects.filter(family=family, assigned_to=request.user, status='review'),
        'done': Task.objects.filter(family=family, assigned_to=request.user, status='done'),
    }
    return render(request, 'core/tasks/kanban.html', {'tasks': tasks})


@login_required
def task_detail(request, task_id):
    """Детальная страница задачи"""
    if not request.user.family:
        return redirect('family_setup')
    
    task = get_object_or_404(Task, id=task_id, family=request.user.family)
    return render(request, 'core/tasks/task_detail.html', {'task': task})


@login_required
def task_create(request):
    """Создание новой задачи"""
    if not request.user.family:
        return redirect('family_setup')
    
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.family = request.user.family
            task.save()
            messages.success(request, 'Задача создана!')
            return redirect('kanban')
    else:
        form = TaskForm()
        form.fields['assigned_to'].queryset = User.objects.filter(family=request.user.family)
    
    return render(request, 'core/tasks/task_form.html', {'form': form, 'title': 'Создать задачу'})


@login_required
def task_edit(request, task_id):
    """Редактирование задачи"""
    if not request.user.family:
        return redirect('family_setup')
    
    task = get_object_or_404(Task, id=task_id, family=request.user.family)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Задача обновлена!')
            return redirect('task_detail', task_id=task.id)
    else:
        form = TaskForm(instance=task)
        form.fields['assigned_to'].queryset = User.objects.filter(family=request.user.family)
    
    return render(request, 'core/tasks/task_form.html', {'form': form, 'title': 'Редактировать задачу'})


@login_required
def task_change_status(request, task_id, status):
    """Быстрое изменение статуса задачи"""
    if not request.user.family:
        return redirect('family_setup')
    
    task = get_object_or_404(Task, id=task_id, family=request.user.family)
    if status in dict(Task.STATUS_CHOICES):
        task.status = status
        task.save()
        messages.success(request, f'Статус задачи "{task.title}" изменён!')
    return redirect('kanban')


# ==================== ДОКУМЕНТЫ ====================

@login_required
def document_list(request):
    """Список документов"""
    if not request.user.family:
        return redirect('family_setup')
    
    documents = Document.objects.filter(family=request.user.family).order_by('-created_at')
    return render(request, 'core/documents/document_list.html', {'documents': documents})


@login_required
def document_upload(request):
    """Загрузка документа"""
    if not request.user.family:
        return redirect('family_setup')
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.family = request.user.family
            doc.save()
            messages.success(request, 'Документ загружен!')
            return redirect('document_list')
    else:
        form = DocumentForm()
    
    return render(request, 'core/documents/document_form.html', {'form': form, 'title': 'Загрузить документ'})


@login_required
def document_detail(request, doc_id):
    """Детальная страница документа"""
    if not request.user.family:
        return redirect('family_setup')
    
    doc = get_object_or_404(Document, id=doc_id, family=request.user.family)
    return render(request, 'core/documents/document_detail.html', {'doc': doc})


# ==================== МЕДИАТЕКА ====================

@login_required
def media_list(request):
    """Список медиафайлов"""
    if not request.user.family:
        return redirect('family_setup')
    
    media_items = MediaItem.objects.filter(family=request.user.family).order_by('-created_at')
    return render(request, 'core/media/media_list.html', {'media_items': media_items})


@login_required
def media_upload(request):
    """Загрузка медиафайла"""
    if not request.user.family:
        return redirect('family_setup')
    
    if request.method == 'POST':
        form = MediaItemForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.uploaded_by = request.user
            media.family = request.user.family
            media.save()
            messages.success(request, 'Файл загружен в медиатеку!')
            return redirect('media_list')
    else:
        form = MediaItemForm()
    
    return render(request, 'core/media/media_upload.html', {'form': form})


@login_required
def media_add_reaction(request, media_id):
    """Добавление/удаление реакции на медиафайл"""
    if not request.user.family:
        return JsonResponse({'success': False, 'error': 'No family'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reaction = data.get('reaction')
            
            media = get_object_or_404(MediaItem, id=media_id, family=request.user.family)
            
            # Инициализируем структуру реакций если её нет
            if not media.reactions:
                media.reactions = {'user_reactions': {}}
            if 'user_reactions' not in media.reactions:
                media.reactions['user_reactions'] = {}
            
            # Добавляем или убираем реакцию
            user_id = str(request.user.id)
            user_reactions = media.reactions['user_reactions']
            
            if user_reactions.get(user_id) == reaction:
                # Убираем реакцию
                del user_reactions[user_id]
            else:
                # Добавляем реакцию
                user_reactions[user_id] = reaction
            
            # Пересчитываем общее количество каждой реакции
            reaction_counts = {}
            for r in dict(MediaItem.REACTION_CHOICES).keys():
                reaction_counts[r] = list(user_reactions.values()).count(r)
                media.reactions[r] = reaction_counts[r]
            
            media.save()
            
            return JsonResponse({
                'success': True,
                'reactions': reaction_counts,
                'user_reaction': user_reactions.get(user_id)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


# ==================== ЧАТЫ ====================

@login_required
def chat_list(request):
    """Список чатов пользователя"""
    if not request.user.family:
        return redirect('family_setup')
    
    user = request.user
    family = user.family
    
    # Приватные чаты пользователя
    private_chats = ChatRoom.objects.filter(
        family=family,
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
    
    # Сортируем по времени последнего сообщения
    chats_with_info.sort(
        key=lambda x: x['last_message'].created_at if x['last_message'] else timezone.now(),
        reverse=True
    )
    
    # Другие пользователи семьи для создания новых чатов
    users = User.objects.filter(family=family).exclude(id=user.id)
    
    context = {
        'private_chats': chats_with_info,
        'users': users,
    }
    return render(request, 'core/chat/chat_list.html', context)


@login_required
def chat_room(request, room_name='general'):
    """Страница чата"""
    if not request.user.family:
        return redirect('family_setup')
    
    user = request.user
    family = user.family
    
    # Получаем или создаём комнату
    if room_name == 'general':
        # Общий чат семьи
        general_room_name = f"general_{family.id}"
        room, created = ChatRoom.objects.get_or_create(
            name=general_room_name,
            defaults={
                'room_type': 'general',
                'family': family
            }
        )
    else:
        # Приватный чат - проверяем доступ
        try:
            room = ChatRoom.objects.get(name=room_name, family=family)
            if room.room_type == 'private':
                if user not in [room.participant1, room.participant2]:
                    return redirect('chat_list')
        except ChatRoom.DoesNotExist:
            return redirect('chat_list')
    
    messages_list = Message.objects.filter(room=room).order_by('created_at')[:100]
    
    context = {
        'messages': messages_list,
        'room': room,
        'room_name': room.name,
    }
    return render(request, 'core/chat/chat_room.html', context)


@login_required
def create_private_chat(request, user_id):
    """Создание приватного чата с другим пользователем"""
    if not request.user.family:
        return redirect('family_setup')
    
    current_user = request.user
    other_user = get_object_or_404(User, id=user_id, family=current_user.family)
    
    # Создаём уникальное имя комнаты
    ids = sorted([current_user.id, other_user.id])
    room_name = f"private_{ids[0]}_{ids[1]}"
    
    room, created = ChatRoom.objects.get_or_create(
        name=room_name,
        defaults={
            'room_type': 'private',
            'family': current_user.family,
            'participant1': current_user,
            'participant2': other_user
        }
    )
    
    return redirect('chat_room', room_name=room.name)


# ==================== УПРАВЛЕНИЕ СЕМЬЁЙ ====================

@login_required
def family_members(request):
    """Список членов семьи"""
    if not request.user.family:
        return redirect('family_setup')
    
    family = request.user.family
    members = User.objects.filter(family=family)
    
    if request.method == 'POST':
        # Удаление участника (только для родителей)
        if request.user.is_parent():
            member_id = request.POST.get('remove_member')
            if member_id and int(member_id) != request.user.id:
                member = get_object_or_404(User, id=member_id, family=family)
                member.family = None
                member.save()
                messages.success(request, f'{member.username} удалён из семьи')
                return redirect('family_members')
    
    context = {
        'members': members,
        'is_parent': request.user.is_parent(),
    }
    return render(request, 'core/family_members.html', context)

# ==================== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ====================

@login_required
def profile_edit(request):
    """Редактирование профиля пользователя"""
    if request.method == 'POST':
        # Обновляем данные пользователя
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        role = request.POST.get('role')
        
        if username:
            request.user.username = username
        if email:
            request.user.email = email
        if phone:
            request.user.phone = phone
        if role and role in dict(User.ROLE_CHOICES):
            request.user.role = role
        
        # Обработка аватара
        if request.FILES.get('avatar'):
            request.user.avatar = request.FILES['avatar']
        
        request.user.save()
        messages.success(request, 'Профиль обновлён!')
        return redirect('profile_edit')
    
    return render(request, 'core/profile_edit.html', {'user': request.user})


# ==================== УПРАВЛЕНИЕ СЕМЬЁЙ (ТОЛЬКО ДЛЯ РОДИТЕЛЕЙ) ====================

@login_required
def family_manage(request):
    """Страница управления семьёй (только для родителей)"""
    if not request.user.family:
        return redirect('family_setup')
    
    if not request.user.is_parent():
        messages.error(request, 'Только родители могут управлять семьёй')
        return redirect('dashboard')
    
    family = request.user.family
    members = User.objects.filter(family=family)
    
    context = {
        'family': family,
        'members': members,
        'member_count': members.count(),
    }
    return render(request, 'core/family_manage.html', context)


@login_required
def family_remove_member(request, user_id):
    """Удаление участника из семьи (только для родителей)"""
    if not request.user.is_parent():
        messages.error(request, 'Только родители могут удалять участников')
        return redirect('dashboard')
    
    if request.user.id == user_id:
        messages.error(request, 'Вы не можете удалить себя из семьи')
        return redirect('family_manage')
    
    member = get_object_or_404(User, id=user_id, family=request.user.family)
    member.family = None
    member.save()
    
    messages.success(request, f'{member.username} удалён из семьи')
    return redirect('family_manage')


@login_required
def family_change_role(request, user_id):
    """Изменение роли участника (только для родителей)"""
    if not request.user.is_parent():
        messages.error(request, 'Только родители могут менять роли')
        return redirect('dashboard')
    
    if request.user.id == user_id:
        messages.error(request, 'Вы не можете изменить свою роль')
        return redirect('family_manage')
    
    new_role = request.POST.get('role')
    if new_role not in dict(User.ROLE_CHOICES):
        messages.error(request, 'Неверная роль')
        return redirect('family_manage')
    
    member = get_object_or_404(User, id=user_id, family=request.user.family)
    member.role = new_role
    member.save()
    
    messages.success(request, f'Роль {member.username} изменена на {member.get_role_display()}')
    return redirect('family_manage')