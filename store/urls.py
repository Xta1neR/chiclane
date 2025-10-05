# store/urls.py
from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    # ---------------- FRONTEND ----------------
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_products, name='category_products'),
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('toggle-wishlist/', views.toggle_wishlist, name='toggle_wishlist'),

    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout_view'),


    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),

    # ---------------- ADMIN DASHBOARD ----------------
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # ---------------- CATEGORY CRUD ----------------
    path('admin-dashboard/categories/', views.manage_categories, name='manage_categories'),
    path('admin-dashboard/category/add/', views.add_category, name='add_category'),
    path('admin-dashboard/category/edit/<int:category_id>/', views.edit_category, name='edit_category'),
    path('admin-dashboard/category/delete/<int:pk>/', views.delete_category, name='delete_category'),

    # ---------------- PRODUCT CRUD ----------------
    path('admin-dashboard/products/', views.manage_products, name='manage_products'),
    path('admin-dashboard/product/add/', views.add_product, name='add_product'),
    path('admin-dashboard/product/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('admin-dashboard/product/delete/<int:pk>/', views.delete_product, name='delete_product'),

    # ---------------- PRODUCT VARIANT CRUD ----------------
    path('admin-dashboard/variants/', views.manage_variants, name='manage_variants'),
    path('admin-dashboard/variant/add/', views.add_variant, name='add_variant'),
    path('admin-dashboard/variant/edit/<int:pk>/', views.edit_variant, name='edit_variant'),
    path('admin-dashboard/variant/delete/<int:pk>/', views.delete_variant, name='delete_variant'),

    # ---------------- PRODUCT IMAGE CRUD ----------------
    path('admin-dashboard/images/', views.manage_images, name='manage_images'),
    path('admin-dashboard/image/add/', views.add_image, name='add_image'),
    path('admin-dashboard/image/edit/<int:pk>/', views.edit_image, name='edit_image'),
    path('admin-dashboard/image/delete/<int:pk>/', views.delete_image, name='delete_image'),
    path('admin-dashboard/product/image/delete/<int:image_id>/', views.delete_product_image, name='delete_product_image'),

    # ---------------- COUPON CRUD ----------------
    path('admin-dashboard/coupons/', views.manage_coupons, name='manage_coupons'),
    path('admin-dashboard/coupon/add/', views.add_coupon, name='add_coupon'),
    path('admin-dashboard/coupon/edit/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
    path('admin-dashboard/coupon/delete/<int:pk>/', views.delete_coupon, name='delete_coupon'),

    # ---------------- ORDERS CRUD ----------------
    # ---------------- ORDERS CRUD ----------------
    path('admin-dashboard/orders/', views.manage_orders, name='manage_orders'),
    path('admin-dashboard/order/<int:order_id>/', views.view_order, name='view_order'),
    path('admin-dashboard/order/update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('admin-dashboard/order/edit/<int:pk>/', views.edit_order, name='edit_order'),
    path('admin-dashboard/order/delete/<int:pk>/', views.delete_order, name='delete_order'),


    # ---------------- USERS CRUD ----------------
    path('admin-dashboard/users/', views.manage_users, name='manage_users'),
    path('admin-dashboard/user/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('admin-dashboard/user/delete/<int:user_id>/', views.delete_user, name='delete_user'),

    # ---------------- CART ----------------
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path("remove-from-cart/", views.remove_from_cart, name="remove_from_cart"),
    path("update-cart-item/", views.update_cart_item, name="update_cart_item"),
    path("checkout/", views.checkout, name="checkout"),
    path("profile/order/<int:order_id>/", views.user_order_detail, name="user_order_detail"),
]
