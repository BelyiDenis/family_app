from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
import secrets
import string


class Family(models.Model):
    """
    Модель семьи - главный изолирующий элемент.
    Каждый пользователь принадлежит к одной семье.
    Все данные (задачи, документы, чаты) привязаны к семье.
    """
    name = models.CharField('Название семьи', max_length=100)
    invite_code = models.CharField('Код приглашения', max_length=10, unique=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    created_by = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_families',
        verbose_name='Создатель'
    )
    
    def save(self, *args, **kwargs):
        if not self.invite_code:
            # Генерируем уникальный код из 6 символов (цифры и заглавные буквы)
            alphabet = string.ascii_uppercase + string.digits
            while True:
                code = ''.join(secrets.choice(alphabet) for _ in range(6))
                if not Family.objects.filter(invite_code=code).exists():
                    self.invite_code = code
                    break
        super().save(*args, **kwargs)
    
    def get_member_count(self):
        """Количество членов семьи"""
        return self.members.count()
    
    def __str__(self):
        return f"{self.name} (код: {self.invite_code})"
    
    class Meta:
        verbose_name = 'Семья'
        verbose_name_plural = 'Семьи'
        ordering = ['-created_at']


class User(AbstractUser):
    """
    Расширенная модель пользователя.
    Привязана к семье через ForeignKey.
    """
    ROLE_CHOICES = (
        ('parent', '👨‍👩 Родитель'),
        ('child', '👶 Ребёнок'),
        ('elder', '👵 Пожилой'),
    )
    
    role = models.CharField('Роль', max_length=10, choices=ROLE_CHOICES, default='child')
    phone = models.CharField('Телефон', max_length=20, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)
    
    # Связь с семьёй (каждый пользователь принадлежит одной семье)
    family = models.ForeignKey(
        Family, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='members',
        verbose_name='Семья'
    )
    
    def __str__(self):
        family_name = self.family.name if self.family else 'без семьи'
        return f"{self.username} ({self.get_role_display()}) - {family_name}"
    
    def is_parent(self):
        return self.role == 'parent'
    
    def is_child(self):
        return self.role == 'child'
    
    def is_elder(self):
        return self.role == 'elder'
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['username']


class Task(models.Model):
    """
    Модель задачи для Kanban-доски.
    Привязана к семье и пользователям внутри этой семьи.
    """
    STATUS_CHOICES = (
        ('todo', '📋 Нужно сделать'),
        ('in_progress', '🔄 В процессе'),
        ('review', '👀 На проверке'),
        ('done', '✅ Сделано'),
    )
    
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    
    # Привязка к семье (изоляция данных)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='tasks', verbose_name='Семья')
    
    created_by = models.ForeignKey(
        User, 
    on_delete=models.CASCADE, 
        related_name='created_tasks', 
        verbose_name='Создал'
    )
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tasks', 
        verbose_name='Ответственный'
    )
    
    deadline = models.DateTimeField('Дедлайн', null=True, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.IntegerField('Приоритет', default=1, help_text='1 - высокий, 5 - низкий')
    
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('task_detail', args=[self.id])
    
    def is_overdue(self):
        """Проверка, просрочена ли задача"""
        if self.deadline and self.status != 'done':
            return timezone.now() > self.deadline
        return False
    
    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-priority', 'deadline']


class Document(models.Model):
    """
    Модель документа в хранилище.
    Привязана к семье.
    """
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
    
    # Привязка к семье (изоляция данных)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='documents', verbose_name='Семья')
    
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Загрузил')
    created_at = models.DateTimeField('Загружен', auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    def is_expired(self):
        """Проверка, просрочен ли документ"""
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False
    
    def days_until_expiry(self):
        """Дней до истечения срока"""
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None
    
    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-created_at']


class MediaItem(models.Model):
    """
    Модель медиафайла (фото/видео) в медиатеке.
    Привязана к семье.
    """
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
    
    # Привязка к семье (изоляция данных)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='media_items', verbose_name='Семья')
    
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Загрузил')
    created_at = models.DateTimeField('Загружено', auto_now_add=True)
    
    # Реакции (лайки и т.д.)
    reactions = models.JSONField('Реакции', default=dict)
    
    def __str__(self):
        return self.title or f"{self.get_type_display()} от {self.created_at.date()}"
    
    def get_reaction_count(self, reaction_type):
        """Получить количество конкретной реакции"""
        return self.reactions.get(reaction_type, 0)
    
    def get_user_reaction(self, user_id):
        """Получить реакцию конкретного пользователя"""
        user_reactions = self.reactions.get('user_reactions', {})
        return user_reactions.get(str(user_id))
    
    def add_reaction(self, reaction_type, user_id):
        """Добавить или убрать реакцию"""
        if reaction_type not in dict(self.REACTION_CHOICES):
            return False
        
        if 'user_reactions' not in self.reactions:
            self.reactions['user_reactions'] = {}
        
        user_reactions = self.reactions['user_reactions']
        
        if user_reactions.get(str(user_id)) == reaction_type:
            # Убираем реакцию
            del user_reactions[str(user_id)]
        else:
            # Добавляем реакцию
            user_reactions[str(user_id)] = reaction_type
        
        # Пересчитываем общее количество каждой реакции
        for reaction in dict(self.REACTION_CHOICES).keys():
            self.reactions[reaction] = list(user_reactions.values()).count(reaction)
        
        self.save()
        return True
    
    class Meta:
        verbose_name = 'Медиафайл'
        verbose_name_plural = 'Медиатека'
        ordering = ['-created_at']


class ChatRoom(models.Model):
    """
    Модель чат-комнаты.
    Привязана к семье. Бывает общего типа (general) и приватные (private).
    """
    ROOM_TYPES = (
        ('general', 'Общий чат'),
        ('private', 'Приватный чат'),
    )
    
    name = models.CharField('Название комнаты', max_length=100, unique=True)
    room_type = models.CharField('Тип чата', max_length=10, choices=ROOM_TYPES, default='general')
    
    # Привязка к семье (изоляция данных)
    family = models.ForeignKey(
        Family, 
        on_delete=models.CASCADE, 
        related_name='chat_rooms', 
        null=True, 
        blank=True, 
        verbose_name='Семья'
    )
    
    # Для приватных чатов - два участника
    participant1 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='chat_participant1',
        verbose_name='Участник 1'
    )
    participant2 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='chat_participant2',
        verbose_name='Участник 2'
    )
    
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    
    def __str__(self):
        if self.room_type == 'private' and self.participant1 and self.participant2:
            return f"Чат: {self.participant1.username} & {self.participant2.username}"
        return self.name
    
    def get_other_user(self, current_user):
        """Получить другого участника приватного чата"""
        if self.room_type != 'private':
            return None
        if self.participant1 == current_user:
            return self.participant2
        return self.participant1
    
    def get_participants(self):
        """Получить список участников"""
        if self.room_type == 'general':
            return self.family.members.all() if self.family else []
        return [self.participant1, self.participant2] if self.participant1 and self.participant2 else []
    
    class Meta:
        verbose_name = 'Чат-комната'
        verbose_name_plural = 'Чат-комнаты'


class Message(models.Model):
    """
    Модель сообщения в чате.
    Привязана к чат-комнате.
    """
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', verbose_name='Комната')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Отправитель')
    content = models.TextField('Сообщение')
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
    
    def mark_as_read(self):
        """Отметить сообщение как прочитанное"""
        if not self.is_read:
            self.is_read = True
            self.save()
    
    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']