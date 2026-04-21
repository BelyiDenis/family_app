from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, Task, Document, MediaItem
from .forms import RegisterForm, TaskForm, DocumentForm, MediaItemForm
from .models import ChatRoom, Message


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


def chat_room(request):
    return render(request, 'core/chat/chat_room.html')