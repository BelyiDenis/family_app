from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('parent', '👨‍👩 Родитель'),
        ('child', '👶 Ребёнок'),
        ('elder', '👵 Пожилой'),
    )
    role = models.CharField('Роль', max_length=10, choices=ROLE_CHOICES, default='child')
    phone = models.CharField('Телефон', max_length=20, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

class Task(models.Model):
    STATUS_CHOICES = (
        ('todo', '📋 Нужно сделать'),
        ('in_progress', '🔄 В процессе'),
        ('review', '👀 На проверке'),
        ('done', '✅ Сделано'),
    )
    
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks', verbose_name='Создал')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks', verbose_name='Ответственный')
    deadline = models.DateTimeField('Дедлайн', null=True, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.IntegerField('Приоритет', default=1)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'

class Document(models.Model):
    CATEGORY_CHOICES = (
        ('passport', '📘 Паспорт'),
        ('birth_cert', '📄 Свидетельство'),
        ('medical', '🏥 Медицина'),
        ('education', '🎓 Образование'),
        ('other', '📁 Другое'),
    )
    
    title = models.CharField('Название', max_length=200)
    file = models.FileField('Файл', upload_to='documents/')
    category = models.CharField('Категория', max_length=20, choices=CATEGORY_CHOICES)
    expiry_date = models.DateField('Срок действия', null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Загрузил')
    created_at = models.DateTimeField('Загружен', auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'

class MediaItem(models.Model):
    TYPE_CHOICES = (
        ('photo', '📷 Фото'),
        ('video', '🎬 Видео'),
    )
    
    title = models.CharField('Название', max_length=200, blank=True)
    file = models.FileField('Файл', upload_to='media/')
    type = models.CharField('Тип', max_length=10, choices=TYPE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Загрузил')
    created_at = models.DateTimeField('Загружено', auto_now_add=True)
    
    def __str__(self):
        return self.title or f"{self.get_type_display()} от {self.created_at.date()}"
    
    class Meta:
        verbose_name = 'Медиафайл'
        verbose_name_plural = 'Медиатека'

class ChatRoom(models.Model):
    ROOM_TYPES = (
        ('general', 'Общий чат'),
        ('private', 'Приватный чат'),
    )
    
    name = models.CharField('Название комнаты', max_length=100, unique=True)
    room_type = models.CharField('Тип чата', max_length=10, choices=ROOM_TYPES, default='general')
    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_participant1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_participant2')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.room_type == 'private' and self.participant1 and self.participant2:
            return f"Чат: {self.participant1.username} & {self.participant2.username}"
        return self.name
    
    def get_other_user(self, current_user):
        if self.participant1 == current_user:
            return self.participant2
        return self.participant1
    
    class Meta:
        verbose_name = 'Чат-комната'
        verbose_name_plural = 'Чат-комнаты'

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField('Сообщение')
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
    
    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']

class MediaItem(models.Model):
    TYPE_CHOICES = (
        ('photo', '📷 Фото'),
        ('video', '🎬 Видео'),
    )
    
    REACTION_CHOICES = (
        ('👍', '👍'),
        ('❤️', '❤️'),
        ('😂', '😂'),
        ('😮', '😮'),
        ('😢', '😢'),
        ('🔥', '🔥'),
    )
    
    title = models.CharField('Название', max_length=200, blank=True)
    file = models.FileField('Файл', upload_to='media/')
    type = models.CharField('Тип', max_length=10, choices=TYPE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Загрузил')
    created_at = models.DateTimeField('Загружено', auto_now_add=True)
    
    # Новые поля для реакций
    reactions = models.JSONField('Реакции', default=dict)
    
    def __str__(self):
        return self.title or f"{self.get_type_display()} от {self.created_at.date()}"
    
    def get_reaction_count(self, reaction_type):
        return self.reactions.get(reaction_type, 0)
    
    def add_reaction(self, reaction_type, user_id):
        if reaction_type not in dict(self.REACTION_CHOICES):
            return
        if 'user_reactions' not in self.reactions:
            self.reactions['user_reactions'] = {}
        self.reactions['user_reactions'][str(user_id)] = reaction_type
        self.save()
    
    class Meta:
        verbose_name = 'Медиафайл'
        verbose_name_plural = 'Медиатека'