from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Category, Brand, Product, UserProfile

class ShopTests(TestCase):
    """ Тестирование логики и безопасности приложения (согласно требованиям проекта) """

    def setUp(self):
        # Подготовка данных перед каждым тестом
        self.client = Client()
        self.user = User.objects.create_user(username='gamer', password='password123')
        
        self.category = Category.objects.create(name='Видеокарты')
        self.brand = Brand.objects.create(name='NVIDIA')
        self.product = Product.objects.create(
            name='RTX 5090',
            description='Флагманская видеокарта',
            price=150000.00,
            stock=10,
            category=self.category,
            brand=self.brand
        )

    def test_product_creation(self):
        """ ТЕСТ 1: Проверка корректного создания товара """
        self.assertEqual(self.product.name, 'RTX 5090')
        self.assertEqual(self.product.price, 150000.00)
        self.assertEqual(self.product.stock, 10)

    def test_user_profile_creation(self):
        """ ТЕСТ 2: Проверка геймификации (Профиль и PC Coins) """
        profile = UserProfile.objects.create(user=self.user, pc_coins=500)
        self.assertEqual(profile.pc_coins, 500)
        self.assertEqual(str(profile), 'Профиль gamer')

    def test_access_cart_unauthenticated(self):
        """ ТЕСТ 3: Проверка защиты авторизации. Гость не должен видеть корзину """
        response = self.client.get('/cart/')
        # Ожидаем редирект на страницу входа (302)
        self.assertEqual(response.status_code, 302)

    def test_product_business_logic(self):
        """ ТЕСТ 4: Проверка кастомных методов модели товара """
        # Так как отзывов еще нет, рейтинг должен быть 0
        self.assertEqual(self.product.get_average_rating(), 0)
        self.assertEqual(self.product.get_review_count(), 0)

    def test_search_functionality(self):
        """ ТЕСТ 5: Проверка логики поиска на главной странице """
        response = self.client.get('/?search=RTX')
        self.assertEqual(response.status_code, 200)