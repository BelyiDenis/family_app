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
    """Список документов с фильтрацией и сортировкой"""
    if not request.user.family:
        return redirect('family_setup')
    
    documents = Document.objects.filter(family=request.user.family)
    
    # Фильтрация по категории
    category = request.GET.get('category', '')
    if category:
        documents = documents.filter(category=category)
    
    # Фильтрация по просроченным
    show_expired = request.GET.get('expired', '')
    if show_expired == 'yes':
        documents = documents.filter(expiry_date__lt=timezone.now().date())
    elif show_expired == 'no':
        documents = documents.filter(expiry_date__gte=timezone.now().date())
    
    # Сортировка
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['title', '-title', 'created_at', '-created_at', 'expiry_date', '-expiry_date']:
        documents = documents.order_by(sort_by)
    else:
        documents = documents.order_by('-created_at')
    
    # Поиск
    search = request.GET.get('search', '')
    if search:
        documents = documents.filter(title__icontains=search)
    
    context = {
        'documents': documents,
        'current_category': category,
        'current_sort': sort_by,
        'current_expired': show_expired,
        'current_search': search,
        'categories': Document.CATEGORY_CHOICES,
        'sort_options': [
            ('-created_at', '📅 Новые сначала'),
            ('created_at', '📅 Старые сначала'),
            ('title', '🔤 Название А-Я'),
            ('-title', '🔤 Название Я-А'),
            ('expiry_date', '⏰ Срок действия (сначала ближайшие)'),
            ('-expiry_date', '⏰ Срок действия (сначала дальние)'),
        ],
    }
    return render(request, 'core/documents/document_list.html', context)

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
    """Список медиафайлов с фильтрацией и сортировкой"""
    if not request.user.family:
        return redirect('family_setup')
    
    media_items = MediaItem.objects.filter(family=request.user.family)
    
    # Фильтрация по типу
    media_type = request.GET.get('type', '')
    if media_type in ['photo', 'video']:
        media_items = media_items.filter(type=media_type)
    
    # Фильтрация по пользователю
    user_id = request.GET.get('user', '')
    if user_id:
        media_items = media_items.filter(uploaded_by_id=user_id)
    
    # Сортировка
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['title', '-title', 'created_at', '-created_at']:
        media_items = media_items.order_by(sort_by)
    else:
        media_items = media_items.order_by('-created_at')
    
    # Поиск
    search = request.GET.get('search', '')
    if search:
        media_items = media_items.filter(title__icontains=search)
    
    # Получаем список пользователей для фильтра
    users = User.objects.filter(family=request.user.family)
    
    context = {
        'media_items': media_items,
        'current_type': media_type,
        'current_sort': sort_by,
        'current_user': user_id,
        'current_search': search,
        'users': users,
        'type_options': [
            ('', 'Все типы'),
            ('photo', '📷 Только фото'),
            ('video', '🎬 Только видео'),
        ],
        'sort_options': [
            ('-created_at', '📅 Новые сначала'),
            ('created_at', '📅 Старые сначала'),
            ('title', '🔤 Название А-Я'),
            ('-title', '🔤 Название Я-А'),
        ],
    }
    return render(request, 'core/media/media_list.html', context)

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
        import json
        try:
            data = json.loads(request.body)
            reaction = data.get('reaction')
        except:
            reaction = request.POST.get('reaction')
        
        media = get_object_or_404(MediaItem, id=media_id, family=request.user.family)
        
        # Добавляем или убираем реакцию
        media.add_reaction(reaction, request.user.id)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'likes': media.likes,
                'hearts': media.hearts,
                'laughs': media.laughs,
                'wows': media.wows,
                'cries': media.cries,
                'fires': media.fires,
                'user_reaction': media.get_user_reaction(request.user.id),
            })
        
        messages.success(request, 'Реакция обновлена!')
        return redirect('media_list')
    
    return redirect('media_list')

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