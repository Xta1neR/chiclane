from django.contrib import admin
from .models import (
    Category, Product, ProductImage, ProductVariant,
    CustomerProfile, CartItem, Order, OrderItem,
    Coupon, LoginActivity, SIZE_CHOICES
)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('sku', 'size', 'color', 'price', 'stock', 'is_active')
    # Make size show as dropdown automatically using choices in the model
    # No need for additional code; Django handles it because of `choices=SIZE_CHOICES`

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_featured", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, ProductVariantInline]
    search_fields = ("name", "description")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'address', 'loyalty_points']
    search_fields = ("user__username", "user__email")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "variant", "price", "quantity")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "payment_status", "total", "created_at")
    inlines = [OrderItemInline]
    list_filter = ("status", "payment_status")
    readonly_fields = ("order_number", "created_at")

admin.site.register(Coupon)
admin.site.register(LoginActivity)
