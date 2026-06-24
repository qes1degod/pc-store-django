from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Product, Review
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json

#  ИМПОРТ ПАГИНАТОРА 
from django.core.paginator import Paginator
from .models import Product, Cart, Order, OrderItem, Favorite, Review, Category, UserProfile

#ADMIN CHECK 
def is_admin(user): 
    return user.is_authenticated and user.is_staff

# HOME (С ИНТЕГРАЦИЕЙ ПАГИНАЦИИ И КАТЕГОРИЙ)
def home(request):
    search = request.GET.get('search', '')
    sort_by = request.GET.get('sort_by')
    category_query = request.GET.get('category')  #ПРОВЕРКА КАТЕГОРИИ 
    
    products = Product.objects.all()
    
    #  ФИЛЬТРАЦИЯ ПО КАТЕГОРИИ 
    if category_query:
        products = products.filter(category__name=category_query)
    
    if search: 
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) | 
            Q(brand__name__icontains=search) | 
            Q(category__name__icontains=search)
        )
        
    if sort_by == 'cheap': 
        products = products.order_by('price')
    elif sort_by == 'expensive': 
        products = products.order_by('-price')
    elif sort_by == 'new': 
        products = products.order_by('-id')

    #  ВНЕДРЕНИЕ ПАГИНАЦИИ 
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    cart_count, favorite_count = 0, 0
    favorites_ids = []
    cart_items = []
    
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        favorite_count = Favorite.objects.filter(user=request.user).count()
        favorites_ids = list(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
        cart_items = Cart.objects.filter(user=request.user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'products_partial.html', {
            'products': page_obj,
            'favorites_ids': favorites_ids
        })
        
    return render(request, 'home.html', {
        'products': page_obj,
        'cart_count': cart_count, 
        'favorite_count': favorite_count, 
        'favorites_ids': favorites_ids, 
        'cart_items': cart_items,
        'search': search
    })

#PROFILE & GAMIFICATION 
@login_required
def profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        return redirect('profile')

    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    total_spent = sum(o.total_price for o in orders if o.status != 'canceled')
    
    rank, next_rank, progress = "Новичок", "Геймер", 0
    if total_spent < 50000:
        progress = (total_spent / 50000) * 100
    elif total_spent < 150000:
        rank, next_rank = "Геймер", "Киберспортсмен"
        progress = ((total_spent - 50000) / 100000) * 100
    else:
        rank, next_rank, progress = "Киберспортсмен", "МАКСИМУМ", 100

    return render(request, 'profile.html', {
        'orders': orders, 'total_spent': total_spent, 'pc_coins': profile.pc_coins, 'rank': rank, 'next_rank': next_rank, 'progress': progress
    })

#PC BUILDER 
def pc_builder(request):
    categories = Category.objects.all()
    products = Product.objects.all()
    return render(request, 'builder.html', {'categories': categories, 'products': products})

@require_POST
def add_build_to_cart(request):
    if not request.user.is_authenticated: return JsonResponse({"error": "login"})
    data = json.loads(request.body)
    product_ids = data.get("product_ids", [])
    for pid in product_ids:
        product = get_object_or_404(Product, id=pid)
        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product, defaults={"quantity": 1})
        if not created:
            cart_item.quantity += 1
            cart_item.save()
    return JsonResponse({"ok": True})

# AUTH
def register(request):
    form = UserCreationForm()
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    return render(request, 'register.html', {'form': form})

# CART 
@require_POST
def add_to_cart(request, product_id):
    if not request.user.is_authenticated: 
        return JsonResponse({"error": "login"})
        
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = Cart.objects.get_or_create(
        user=request.user, 
        product=product, 
        defaults={"quantity": 1}
    )
    if not created: 
        cart_item.quantity += 1
        cart_item.save()
        
    return JsonResponse({
        "ok": True, 
        "count": Cart.objects.filter(user=request.user).count(),
        "item_id": cart_item.id,
        "quantity": cart_item.quantity
    })

def update_cart(request):
    if not request.user.is_authenticated: 
        return JsonResponse({"ok": False})
        
    data = json.loads(request.body)
    item = get_object_or_404(Cart, id=data.get("item_id"), user=request.user)
    
    if data.get("action") == "plus":
        item.quantity += 1
    else:
        item.quantity -= 1
        
    if item.quantity <= 0:
        item.delete()
        current_qty = 0
    else:
        item.save()
        current_qty = item.quantity
        
    items = Cart.objects.filter(user=request.user)
    total = sum(i.product.price * i.quantity for i in items)
    
    return JsonResponse({
        "ok": True, 
        "total": float(total), 
        "cart_count": items.count(),
        "current_qty": current_qty
    })

def remove_from_cart(request, cart_id):
    Cart.objects.filter(id=cart_id, user=request.user).delete()
    items = Cart.objects.filter(user=request.user)
    total = sum(i.product.price * i.quantity for i in items)
    
    return JsonResponse({
        "ok": True, 
        "total": float(total), 
        "cart_count": items.count()
    })

@require_POST
def toggle_favorite(request, product_id):
    if not request.user.is_authenticated: return JsonResponse({"ok": False, "error": "login"})
    favorite, created = Favorite.objects.get_or_create(user=request.user, product_id=product_id)
    if not created: favorite.delete()
    return JsonResponse({"ok": True, "liked": created, "count": Favorite.objects.filter(user=request.user).count()})

#PAGES 
def favorites(request):
    if not request.user.is_authenticated: return redirect('login')
    return render(request, "favorites.html", {"items": Favorite.objects.filter(user=request.user)})

def cart(request):
    if not request.user.is_authenticated: return redirect("login")
    items = Cart.objects.filter(user=request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, "cart.html", {"items": items, "total": sum(i.product.price * i.quantity for i in items), "pc_coins": profile.pc_coins})

def orders_list(request):
    if not request.user.is_authenticated: return redirect('login')
    orders = Order.objects.all().order_by('-id') if request.user.is_staff else Order.objects.filter(user=request.user).order_by('-id')
    return render(request, 'orders.html', {'orders': orders})

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all().order_by('-created_at')
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id).order_by('?')[:4]
    favorites_ids = list(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)) if request.user.is_authenticated else []
    if request.method == "POST":
        if not request.user.is_authenticated: return redirect("login")
        Review.objects.create(product=product, user=request.user, rating=int(request.POST.get('rating', 5)), text=request.POST.get('text', ''))
        return redirect('product_detail', product_id=product.id)
    return render(request, "product_detail.html", {"product": product, "reviews": reviews, "related_products": related_products, "favorites_ids": favorites_ids})

# CREATE ORDER 
def create_order(request):
    if not request.user.is_authenticated: return redirect("login")
    if request.method == "POST":
        items = Cart.objects.filter(user=request.user)
        if not items.exists(): return redirect("cart")
        
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        base_total = sum(i.product.price * i.quantity for i in items)
        
        discount = base_total * 10 / 100 if request.POST.get('promo_code', '') == "PCSTORE10" else 0
        d_type = request.POST.get('delivery_type', 'pickup')
        delivery_price = 500 if d_type == 'courier' else 0
        
        final_total = base_total - discount + delivery_price

        spend_coins = int(request.POST.get('spend_coins', 0))
        if spend_coins > profile.pc_coins: spend_coins = profile.pc_coins
        if spend_coins > final_total: spend_coins = int(final_total)
        final_total -= spend_coins
        profile.pc_coins -= spend_coins

        cashback = int(final_total * 5 / 100)
        profile.pc_coins += cashback
        profile.save()

        order = Order.objects.create(
            user=request.user, first_name=request.POST.get('first_name', ''), last_name=request.POST.get('last_name', ''),
            phone=request.POST.get('phone', ''), email=request.user.email, delivery_type=d_type,
            address=request.POST.get('address', ''), comment=request.POST.get('comment', ''), total_price=final_total
        )
        for i in items: OrderItem.objects.create(order=order, product=i.product, quantity=i.quantity)
        items.delete()

        async_to_sync(get_channel_layer().group_send)(
            "dashboard", {"type": "send_event", "data": {"type": "new_order", "message": f"Заказ #{order.id} на {final_total} ₽ (+{cashback} 🪙)", "order_id": order.id}}
        )
        return redirect("orders")
    return redirect("cart")

def payment_page(request, order_id): return render(request, "payment.html", {"order": get_object_or_404(Order, id=order_id, user=request.user)})
def apply_promo(request): return JsonResponse({"discount": 10 if json.loads(request.body).get("code") == "PCSTORE10" else 0})

# ================= ADMIN DASHBOARD =================
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request): 
    return render(request, "admin_dashboard/dashboard.html", {"users_count": User.objects.count(), "products_count": Product.objects.count(), "orders_count": Order.objects.count(), "latest_orders": Order.objects.all().order_by("-id")[:10]})

@login_required
@user_passes_test(is_admin)
def admin_products(request): 
    return render(request, "admin_dashboard/products.html", {"products": Product.objects.all()})

@login_required
@user_passes_test(is_admin)
def admin_orders(request): 
    return render(request, "admin_dashboard/orders.html", {"orders": Order.objects.all().order_by("-id")})

@login_required
@user_passes_test(is_admin)
def admin_users(request): 
    return render(request, "admin_dashboard/users.html", {"users": User.objects.all()})

@login_required
@user_passes_test(is_admin)
def admin_stats_api(request): 
    return JsonResponse({"users": User.objects.count(), "products": Product.objects.count(), "orders": Order.objects.count()})

@login_required
@user_passes_test(is_admin)
def admin_settings(request): 
    return render(request, "admin_dashboard/settings.html")

@require_POST
def api_update_order_status(request):
    if not request.user.is_staff: 
        return JsonResponse({"ok": False, "error": "Доступ запрещен"})
    data = json.loads(request.body)
    order = get_object_or_404(Order, id=data.get('order_id'))
    order.status = data.get('status')
    order.save()
    return JsonResponse({"ok": True})

@require_POST
def api_update_product_name(request):
    if not request.user.is_staff: 
        return JsonResponse({"ok": False, "error": "Доступ запрещен"})
    data = json.loads(request.body)
    product = get_object_or_404(Product, id=data.get('product_id'))
    product.name = data.get('name')
    product.save()
    return JsonResponse({"ok": True})

@require_POST
def add_review(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "login"})
    
    try:
        data = json.loads(request.body)
        rating = int(data.get('rating', 5))
        text = data.get('text', '').strip()
        
        if not text:
            return JsonResponse({"ok": False, "error": "Отзыв не может быть пустым"})
            
        product = Product.objects.get(id=product_id)
        
        Review.objects.create(
            product=product,
            user=request.user,
            rating=rating,
            text=text
        )
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

# REST API 
def api_products_list(request):
    """ REST API Endpoint: Возвращает список всех товаров в формате JSON """
    products = Product.objects.all()
    data = []
    for p in products:
        data.append({
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "brand": p.brand.name if p.brand else None,
            "category": p.category.name if p.category else None,
            "stock": p.stock
        })
    return JsonResponse({"status": "success", "count": len(data), "data": data})

# КАСТОМНЫЕ СБОРКИ
def custom_build(request):
    if request.method == "POST":
        return render(request, "custom_build_success.html")
    return render(request, "custom_build.html")
#  ИНФОРМАЦИОННЫЕ СТРАНИЦЫ 
def info_page(request, slug):
    pages = {
        'contacts': {
            'title': 'Контакты', 
            'icon': 'bi-telephone-fill',
            'content': '''
                <div class="row g-4 mt-2">
                    <div class="col-md-6">
                        <h4 class="fw-bold mb-3"><i class="bi bi-geo-alt-fill text-primary me-2"></i> Главный офис</h4>
                        <p class="fs-5"><strong>Телефон:</strong> +7 968 X22 13 XX<br>
                        <strong>Email:</strong> PCSTORE@mail.ru<br>
                        <strong>Адрес:</strong> г. Санкт-Петербург, Исаакиевская пл., 4, лит. А, 190000</p>
                        <p class="fs-5"><strong>График работы:</strong><br>Пн-Пт 11:00—19:00<br>Сб-Вс 12:00-18:00</p>
                    </div>
                    <div class="col-md-6">
                        <h4 class="fw-bold mb-3"><i class="bi bi-headset text-success me-2"></i> Поддержка клиентов</h4>
                        <p class="fs-5 text-secondary">По вопросам сборок, возврату и статусу заказов:</p>
                        <p class="fs-5"><strong>Телефон:</strong> +7 (812) 555-01-99<br>
                        <strong>Email:</strong> support@pcstore.ru</p>
                        
                        <h4 class="fw-bold mb-3 mt-5"><i class="bi bi-briefcase-fill text-warning me-2"></i> Сотрудничество (B2B)</h4>
                        <p class="fs-5 text-secondary">Для коммерческих предложений и рекламы:</p>
                        <p class="fs-5"><strong>Телефон:</strong> +7 (495) 777-88-22<br>
                        <strong>Email:</strong> b2b@pcstore.ru</p>
                    </div>
                </div>
            '''
        },
        'delivery': {
            'title': 'Оплата и доставка', 
            'icon': 'bi-truck',
            'content': '<b>Доставка:</b><br>Мы доставляем заказы курьером до двери (500 ₽) или предлагаем бесплатный самовывоз из нашего магазина.<br><br><b>Оплата:</b><br>Принимаем банковские карты, наличные, а также списание баллов PC Coins до 100% от стоимости.'
        },
        'warranty': {
            'title': 'Гарантия', 
            'icon': 'bi-shield-check',
            'content': 'Мы уверены в качестве наших сборок. На все ПК действует расширенная гарантия от магазина — до 5 лет.<br><br>В случае неисправности наш курьер бесплатно заберет ПК, а инженеры починят его за 24 часа.'
        },
        'reviews': {
            'title': 'Отзывы клиентов', 
            'icon': 'bi-star-fill',
            'content': 'Более 2000 геймеров уже выбрали PC STORE. Раздел с живыми отзывами и фото сборок от покупателей находится в стадии заполнения.'
        },
        'promos': {
            'title': 'Акции и бонусы', 
            'icon': 'bi-gift-fill',
            'content': '🎉 <b>Акция месяца:</b> Введите промокод <b>PCSTORE</b> при оформлении заказа и получите скидку 10%!<br><br>За каждую покупку мы начисляем 5% кэшбека в виде PC Coins на ваш аккаунт.'
        },
        'privacy': {
            'title': 'Политика конфиденциальности', 
            'icon': 'bi-file-earmark-lock-fill',
            'content': 'Ваши данные под надежной защитой. Мы используем современные протоколы шифрования и никогда не передаем личную информацию третьим лицам.'
        },
    }
    
    page = pages.get(slug, {
        'title': 'Страница в разработке', 
        'icon': 'bi-tools',
        'content': 'Наши разработчики уже работают над этой страницей. Возвращайтесь чуть позже!'
    })
    
    return render(request, 'info_page.html', {'page': page})