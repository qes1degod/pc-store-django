from django.urls import path
from shop import views
from django.contrib import admin
from django.contrib.auth.views import LogoutView, LoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('custom-build/', views.custom_build, name='custom_build'),
    path('info/<str:slug>/', views.info_page, name='info_page'),
    
    #  Конфигуратор ПК
    path('builder/', views.pc_builder, name='builder'),
    path('add-build/', views.add_build_to_cart, name='add_build_to_cart'),

    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('favorites/', views.favorites, name='favorites'),
    path('favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('order/', views.create_order, name='create_order'),
    path('orders/', views.orders_list, name='orders'),
    path('payment/<int:order_id>/', views.payment_page, name='payment'),
    path('promo/', views.apply_promo, name='apply_promo'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('admin/', admin.site.urls),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/products/', views.admin_products, name='admin_products'),
    path('admin-dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('admin-dashboard/users/', views.admin_users, name='admin_users'),
    path('admin-dashboard/stats/', views.admin_stats_api, name='admin_stats_api'),
    path('admin-dashboard/settings/', views.admin_settings, name='admin_settings'),
    path('api/admin/order-status/', views.api_update_order_status, name='api_update_order_status'),
    path('api/admin/product-name/', views.api_update_product_name, name='api_update_product_name'),
    path('product/<int:product_id>/add_review/', views.add_review, name='add_review'),
    path('api/products/', views.api_products_list, name='api_products_list'),
]