from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg

class Category(models.Model):
    """ Модель категории комплектующих """
    name = models.CharField(max_length=100, verbose_name="Название")
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']
        
    def __str__(self): return self.name

class Brand(models.Model):
    """ Модель бренда (производителя) """
    name = models.CharField(max_length=100, verbose_name="Бренд")
    
    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self): return self.name

# Модель Тегов для связи ManyToMany
class Tag(models.Model):
    """ Модель тегов для товаров """
    name = models.CharField(max_length=50, verbose_name="Имя тега")
    
    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        
    def __str__(self): return self.name

class Product(models.Model):
    """ Основная модель товара с бизнес-логикой рейтингов """
    name = models.CharField(max_length=200, verbose_name="Название товара")
    description = models.TextField(verbose_name="Описание")
    image = models.URLField(blank=True, null=True, verbose_name="URL Изображения")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    stock = models.PositiveIntegerField(default=0, verbose_name="В наличии")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Категория")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, verbose_name="Бренд")
    
    # 🔥 НОВОЕ: Связь ManyToMany (Требование проекта)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Теги товара")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-price'] 

    def __str__(self): return self.name
    
    def get_average_rating(self):
        """ Кастомный метод: подсчет среднего рейтинга по отзывам """
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg is not None else 0
        
    def get_review_count(self):
        """ Кастомный метод: количество отзывов """
        return self.reviews.count()

class Cart(models.Model):
    """ Модель корзины покупателя """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    
    class Meta:
        verbose_name = "Товар в корзине"
        verbose_name_plural = "Корзины пользователей"

class Order(models.Model):
    """ Модель заказа с отслеживанием статусов """
    STATUS_CHOICES = (
        ('new', 'Новый'), ('processing', 'В сборке'), ('paid', 'Оплачен'), 
        ('shipped', 'В пути'), ('done', 'Получен'), ('canceled', 'Отменен')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус заказа")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Сумма")
    first_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Имя")
    last_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Фамилия")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    delivery_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="Тип доставки")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адрес")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    promo_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Промокод")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    def get_progress(self):
        """ Кастомный метод: возврат процента выполнения заказа для трекера """
        return {'new': 10, 'processing': 40, 'paid': 60, 'shipped': 80, 'done': 100, 'canceled': 0}.get(self.status, 0)

class OrderItem(models.Model):
    """ Модель товара внутри конкретного заказа """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    
    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказах"

class Favorite(models.Model):
    """ Модель списка желаемого (Избранное) """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    
    class Meta:
        verbose_name = "Избранный товар"
        verbose_name_plural = "Избранные товары"

class Review(models.Model):
    """ Модель отзывов с рейтинговой системой """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name="Товар")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    rating = models.PositiveSmallIntegerField(default=5, verbose_name="Оценка")
    text = models.TextField(blank=True, null=True, verbose_name="Текст отзыва")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата написания")
    
    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']

class UserProfile(models.Model):
    """ Модель геймификации: Профиль с бонусным балансом """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Пользователь")
    pc_coins = models.PositiveIntegerField(default=0, verbose_name="Баланс PC Coins")

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"Профиль {self.user.username}"