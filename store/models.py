# store/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

import uuid

SIZE_CHOICES = [
    ("XS", "XS"),
    ("S", "S"),
    ("M", "M"),
    ("L", "L"),
    ("XL", "XL"),
]

ORDER_STATUS = [
    ("PENDING", "Pending"),
    ("PACKED", "Packed"),
    ("SHIPPED", "Shipped"),
    ("OUT_FOR_DELIVERY", "Out for delivery"),
    ("DELIVERED", "Delivered"),
    ("RETURNED", "Returned"),
    ("CANCELLED", "Cancelled"),
]

PAYMENT_STATUS = [
    ("PENDING", "Pending"),
    ("PAID", "Paid"),
    ("REFUNDED", "Refunded"),
]


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='subcategories'
    )

    # keep one "default" image if you want, but slideshow will come from related images
    image = models.ImageField(upload_to="category_images/", blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.parent.name} -> {self.name}" if self.parent else self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class CategoryImage(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="category_images/")

    def __str__(self):
        return f"Image for {self.category.name}"


class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products"
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_price(self):
        return self.discounted_price if self.discounted_price else self.price

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("store:product_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    color = models.CharField(max_length=80, blank=True)  # optional for variant

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=120, unique=True)
    size = models.CharField(max_length=4, choices=SIZE_CHOICES)
    color = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("product", "size", "color", "sku")

    def __str__(self):
        return f"{self.product.name} - {self.color} / {self.size}"

    def get_price(self):
        return self.price if self.price is not None else self.product.get_price()


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=100, blank=True) 
    phone_number = models.CharField(max_length=10, blank=True)
    address = models.TextField(blank=True)
    loyalty_points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Profile: {self.user.username}"


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        # Try to create profile, ignore if already exists
        try:
            CustomerProfile.objects.create(user=instance)
        except IntegrityError:
            pass






class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='wishlist_items')
    variant = models.ForeignKey('ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'variant')
        ordering = ['-created_at']

    def __str__(self):
        variant_text = f" ({self.variant.size})" if self.variant else ""
        return f"{self.user.username} - {self.product.name}{variant_text}"


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def line_total(self):
        return self.variant.get_price() * self.quantity



class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    order_number = models.CharField(max_length=40, unique=True, blank=True)
    status = models.CharField(max_length=30, choices=ORDER_STATUS, default="PENDING")
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS, default="PENDING")
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    shipping_address = models.TextField()
    phone_number = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"Order {self.order_number} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = str(uuid.uuid4()).split('-')[0].upper()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def line_total(self):
        return self.price * self.quantity




class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_percent = models.PositiveIntegerField(default=0)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    def is_valid(self, total_amount=0):
        """
        Check if coupon is valid at current time and 
        if minimum amount condition is satisfied.
        """
        now = timezone.now()
        return (
            self.active
            and self.start_date <= now <= self.end_date
            and total_amount >= self.min_amount
        )

    def get_discount(self, total_amount):
        """
        Calculate discount for a given total cart/order amount.
        Returns discount value (not final total).
        """
        if self.is_valid(total_amount):
            return (total_amount * self.discount_percent) / 100
        return 0



class LoginActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_activity")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
