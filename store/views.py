# store/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from django.utils.text import slugify
import re, traceback
from django.db import IntegrityError, transaction
from django.urls import reverse



from .models import (
    Product, ProductVariant, ProductImage, Category, SIZE_CHOICES,
    CartItem, Order, OrderItem, Coupon, Wishlist, CustomerProfile, CategoryImage, Coupon,
)
from .forms import (
    CategoryForm, ProductForm, ProductVariantForm, ProductImageForm,
    CouponForm, CheckoutForm, AddToCartForm, CustomerProfileForm,
    ApplyCouponForm,
)

# ------------------ FRONTEND VIEWS ------------------

def generate_unique_slug(name, product_id=None):
    """
    Generate a unique slug for a product.
    If product_id is provided, ignore that product when checking uniqueness (for editing).
    """
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    while Product.objects.filter(slug=slug).exclude(id=product_id).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug

def home(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    top_categories = Category.objects.filter(parent__isnull=True)
    return render(request, 'store/home.html', {'featured_products': featured_products, 'top_categories': top_categories})

def product_list(request):
    query = request.GET.get('q', '')
    selected_categories = request.GET.getlist('category')
    products = Product.objects.filter(is_active=True)

    if query:
        products = products.filter(name__icontains=query)

    if selected_categories:
        all_category_ids = []
        for cat_id in selected_categories:
            try:
                category = Category.objects.get(id=cat_id)
                all_category_ids.append(category.id)
                child_ids = category.subcategories.all().values_list('id', flat=True)
                all_category_ids.extend(child_ids)
            except Category.DoesNotExist:
                continue
        products = products.filter(category__id__in=all_category_ids)

    # ✅ Get wishlist product IDs for logged-in user
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'products': products,
        'all_categories': Category.objects.all(),
        'query': query,
        'selected_categories': selected_categories,
        'wishlist_product_ids': wishlist_product_ids,  # send to template
    }
    return render(request, 'store/product_list.html', context)



def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    variants = product.variants.filter(is_active=True)

    # Get all product IDs in the user's wishlist
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    in_wishlist = product.id in wishlist_product_ids

    # Related products (same category, excluding current product)
    related_products = []
    if product.category:
        related_products = product.category.products.filter(is_active=True).exclude(id=product.id)[:8]

    return render(request, "store/product_detail.html", {
        "product": product,
        "variants": variants,
        "in_wishlist": in_wishlist,
        "related_products": related_products,
        "wishlist_product_ids": wishlist_product_ids,
    })



@require_POST
def add_to_cart(request):
    if request.method == "POST":
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))

        variant = get_object_or_404(ProductVariant, id=variant_id)

        if request.user.is_authenticated:
            # Logged in → use user field
            cart_item, created = CartItem.objects.get_or_create(
                user=request.user,
                variant=variant,
                defaults={"quantity": quantity},
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
        else:
            # Guest user → use session_key
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key

            cart_item, created = CartItem.objects.get_or_create(
                session_key=session_key,
                variant=variant,
                defaults={"quantity": quantity},
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

    return redirect(request.META.get("HTTP_REFERER", "store:home"))


def remove_from_cart(request):
    if request.method == "POST":
        cart_item_id = request.POST.get("cart_item_id")
        cart_item = get_object_or_404(CartItem, id=cart_item_id)

        # Only allow removing if user owns it (safety)
        if request.user.is_authenticated:
            if cart_item.user == request.user:
                cart_item.delete()
        else:
            if cart_item.session_key == request.session.session_key:
                cart_item.delete()

    return redirect("store:cart")

def update_cart_item(request):
    if request.method == "POST":
        cart_item_id = request.POST.get("cart_item_id")
        variant_id = request.POST.get("variant_id")

        cart_item = get_object_or_404(CartItem, id=cart_item_id)
        new_variant = get_object_or_404(ProductVariant, id=variant_id, product=cart_item.variant.product)

        # Security check: ensure item belongs to this session or user
        if request.user.is_authenticated:
            if cart_item.user != request.user:
                return redirect("store:cart")
        else:
            if cart_item.session_key != request.session.session_key:
                return redirect("store:cart")

        # ✅ Update variant
        cart_item.variant = new_variant
        cart_item.save()

    return redirect("store:cart")


def cart_view(request):
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user)
    else:
        session_key = request.session.session_key or request.session.create()
        items = CartItem.objects.filter(session_key=session_key)

    total = sum([item.line_total() for item in items]) if items else 0
    return render(request, "store/cart.html", {"items": items, "total": total})

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)

    # Get subcategories of this category
    subcategories = category.subcategories.all()

    if subcategories.exists():  # parent category
        # Get all products in subcategories
        products = Product.objects.filter(category__in=subcategories)
    else:
        # Single category with no subcategories
        products = Product.objects.filter(category=category)

    return render(request, "store/category_products.html", {
        "category": category,
        "subcategories": subcategories,  # pass subcategories to template
        "products": products,
    })




@login_required
def place_order(request):
    if request.method == "POST":
        # gather form data
        full_name = request.POST.get("full_name")
        address = request.POST.get("address")
        phone = request.POST.get("phone")

        cart_items = CartItem.objects.filter(user=request.user)
        total = sum(item.line_total() for item in cart_items)

        order = Order.objects.create(
            user=request.user,
            shipping_address=address,
            phone_number=phone,
            total=total,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.variant.product,
                variant=item.variant,
                price=item.variant.get_price(),
                quantity=item.quantity,
            )
        

        cart_items.delete()  # clear cart after order placement

        messages.success(request, "Your order has been placed successfully!")
        return redirect("store:profile")


@login_required
def order_success(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})


from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from .models import CartItem, Order, OrderItem, Coupon, CustomerProfile
from .forms import CheckoutForm, ApplyCouponForm

@login_required
def user_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.select_related("product", "variant")
    return render(request, "store/user_order_detail.html", {
        "order": order,
        "order_items": order_items,
    })


@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("store:cart")

    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    # Pre-fill form
    initial_data = {
        "full_name": profile.full_name or request.user.username,
        "phone_number": profile.phone_number,
        "address": profile.address,
    }

    total = sum(ci.line_total() for ci in cart_items)
    discount = Decimal(0)
    final_total = total
    applied_coupon = None

    form = CheckoutForm(request.POST or None, initial=initial_data)
    coupon_form = ApplyCouponForm(request.POST or None)

    # ✅ Handle POST
    if request.method == "POST":
        # ---- APPLY COUPON ----
        if "apply_coupon" in request.POST:
            if coupon_form.is_valid():
                code = coupon_form.cleaned_data["code"].strip()
                try:
                    coupon = Coupon.objects.get(code__iexact=code, active=True)
                    if coupon.start_date <= timezone.now() <= coupon.end_date and total >= coupon.min_amount:
                        discount = (total * coupon.discount_percent) / 100
                        final_total = total - discount
                        applied_coupon = coupon
                        request.session["coupon_code"] = coupon.code
                        messages.success(request, f"Coupon '{coupon.code}' applied! You saved ₹{discount:.2f}")
                    else:
                        messages.error(request, "Coupon is inactive, expired, or minimum amount not met.")
                except Coupon.DoesNotExist:
                    messages.error(request, "Invalid coupon code.")

        # ---- PLACE ORDER ----
        elif "place_order" in request.POST:
            if form.is_valid():
                coupon = None
                coupon_code = request.session.get("coupon_code")

                # Apply existing coupon if still valid
                if coupon_code:
                    try:
                        coupon = Coupon.objects.get(code=coupon_code, active=True)
                        if coupon.start_date <= timezone.now() <= coupon.end_date and total >= coupon.min_amount:
                            discount = (total * coupon.discount_percent) / 100
                            final_total = total - discount
                            applied_coupon = coupon
                    except Coupon.DoesNotExist:
                        pass

                # ✅ Create the Order
                order = Order.objects.create(
                    user=request.user,
                    total=final_total,
                    discount=discount,
                    shipping_address=form.cleaned_data["address"],
                    phone_number=form.cleaned_data["phone_number"],
                )

                # ✅ Create OrderItems
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.variant.product,
                        variant=item.variant,
                        price=item.variant.get_price(),
                        quantity=item.quantity,
                    )

                # ✅ Update Customer Profile
                profile.full_name = form.cleaned_data["full_name"]
                profile.phone_number = form.cleaned_data["phone_number"]
                profile.address = form.cleaned_data["address"]
                profile.save()

                # ✅ Clear cart and session
                cart_items.delete()
                request.session.pop("coupon_code", None)

                messages.success(request, "Order placed successfully!")
                return redirect(reverse("store:profile") + "#orders")
            else:
                messages.error(request, "Please fix the errors in the form before placing your order.")

    # ---- RENDER PAGE ----
    final_total = total - discount
    return render(request, "store/checkout.html", {
        "cart_items": cart_items,
        "total": total,
        "discount": discount,
        "final_total": final_total,
        "applied_coupon": applied_coupon,
        "form": form,
        "coupon_form": coupon_form,
    })




@login_required
def wishlist_view(request):
    wishlist_items = []
    if request.user.is_authenticated:
        # Get all wishlist items for the logged-in user
        wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')

    return render(request, "store/wishlist.html", {
        "wishlist_items": wishlist_items
    })


@require_POST
@login_required
def toggle_wishlist(request):
    product_id = request.POST.get("product_id")
    variant_id = request.POST.get("variant_id")  # optional
    if not product_id:
        messages.error(request, "No product selected.")
        return redirect("store:home")

    product = get_object_or_404(Product, id=product_id)
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id)

    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product,
        variant=variant
    )

    if not created:
        wishlist_item.delete()
        messages.success(request, f"Removed {product.name} from wishlist.")
    else:
        messages.success(request, f"Added {product.name} to wishlist.")

    return redirect(request.META.get("HTTP_REFERER", "store:home"))






@login_required
def profile_view(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('store:profile')
    else:
        form = CustomerProfileForm(instance=profile, user=request.user)

    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    wishlist = Wishlist.objects.filter(user=request.user)

    context = {
        'form': form,
        'orders': orders,
        'wishlist': wishlist,
    }
    return render(request, 'store/profile.html', context)

@login_required
def edit_profile_view(request):
    profile = request.user.customerprofile
    if request.method == "POST":
        form = CustomerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('store:profile')
    else:
        form = CustomerProfileForm(instance=profile)
    return render(request, 'store/edit_profile.html', {'form': form})


def signup_view(request):
    if request.method == "POST":
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''

        # Basic validations
        if not name or not re.match(r'^[A-Za-z ]+$', name):
            messages.error(request, "Name must contain only letters and spaces.")
            return render(request, 'store/signup.html')
        if not email:
            messages.error(request, "Email is required.")
            return render(request, 'store/signup.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return render(request, 'store/signup.html')
        if not password:
            messages.error(request, "Password is required.")
            return render(request, 'store/signup.html')

        # Generate unique username
        base_username = re.sub(r'\s+', '', name).lower() or "user"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        try:
            with transaction.atomic():
                # Create the user
                user = User.objects.create_user(username=username, email=email, password=password)

                # Create profile and save full_name
                profile, _ = CustomerProfile.objects.get_or_create(user=user)
                profile.full_name = name
                profile.save()

            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('store:profile')

        except IntegrityError as e:
            print("Signup Error:", e)
            messages.error(request, "An error occurred. Please try again later.")
            return render(request, 'store/signup.html')

    return render(request, 'store/signup.html')


def logout_view(request):
    logout(request)
    return redirect('store:home')


def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next') or None

    if request.method == "POST":
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''

        # Get username from email
        try:
            username = User.objects.get(email=email).username
        except User.DoesNotExist:
            messages.error(request, "Invalid email or password.")
            return render(request, 'store/login.html', {'next': next_url})

        # Authenticate
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Priority redirect: admin > next_url > product list
            if user.is_staff or user.is_superuser:
                return redirect('store:admin_dashboard')
            if next_url:
                return redirect(next_url)

            return redirect('store:product_list')
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, 'store/login.html', {'next': next_url})



# ------------------ ADMIN DECORATOR ------------------

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_staff, login_url='store:login')(view_func)

# ------------------ ADMIN DASHBOARD ------------------

@admin_required
def admin_dashboard(request):
    return render(request, "store/admin_dashboard.html", {
        "total_products": Product.objects.count(),
        "total_orders": Order.objects.count(),
        "total_users": User.objects.count()
    })

# ------------------ ORDERS ------------------

@admin_required
def manage_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, "store/manage_orders.html", {"orders": orders})

# View order details
def view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.select_related("product", "variant")

    return render(request, "store/view_order.html", {
        "order": order,
        "order_items": order_items,
    })


# Update order status
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status and new_status in dict(Order._meta.get_field("status").choices):
            order.status = new_status
            order.save()
            messages.success(request, f"Order {order.order_number} status updated to {new_status}.")
            return redirect("store:manage_orders")
        else:
            messages.error(request, "Invalid status selected.")

    return render(request, "store/update_order_status.html", {
        "order": order,
        "status_choices": Order._meta.get_field("status").choices,
    })

@admin_required
def edit_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, "store/edit_order.html", {"order": order})

@admin_required
def delete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.delete()
    messages.success(request, "Order deleted successfully.")
    return redirect("store:manage_orders")

# ------------------ USERS ------------------

@admin_required
def manage_users(request):
    users = User.objects.all()
    return render(request, "store/manage_users.html", {"users": users})

@admin_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.is_staff = "is_admin" in request.POST
        user.save()
        return redirect('store:manage_users')
    return render(request, 'store/edit_user.html', {'user': user})

@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect('store:manage_users')
    return render(request, 'store/confirm_delete_user.html', {'user': user})

# ------------------ CATEGORY CRUD ------------------

# Manage categories
@admin_required
def manage_categories(request):
    categories = Category.objects.all()
    return render(request, "store/manage_categories.html", {"categories": categories})


# Add category
@admin_required
def add_category(request):
    parent_categories = Category.objects.filter(parent__isnull=True)

    if request.method == "POST":
        name = request.POST.get("name")
        is_parent = "is_parent" in request.POST
        parent_id = request.POST.get("parent") or None

        category = Category(name=name)
        if is_parent:
            category.parent = None
        elif parent_id:
            category.parent = Category.objects.get(id=parent_id)

        category.description = request.POST.get("description")

        # Generate unique slug
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Category.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        category.slug = slug

        category.save()

        # ✅ Save multiple images for parent categories
        if is_parent:
            images = request.FILES.getlist("images")
            for img in images:
                CategoryImage.objects.create(category=category, image=img)

        messages.success(request, "Category added successfully!")
        return redirect("store:manage_categories")

    return render(request, "store/add_category.html", {"categories": parent_categories})


@admin_required
def edit_category(request, category_id):
    category = Category.objects.get(id=category_id)
    categories = Category.objects.exclude(id=category.id)

    if request.method == "POST":
        new_name = request.POST.get("name")
        is_parent = "is_parent" in request.POST
        parent_id = request.POST.get("parent") or None
        description = request.POST.get("description")
        new_images = request.FILES.getlist("images")  # multiple new images

        category.name = new_name
        category.description = description

        # Delete removed existing images
        for img in category.images.all():
            if not request.POST.get(f"keep_image_{img.id}"):
                img.delete()

        # Save newly uploaded images
        for img in new_images:
            CategoryImage.objects.create(category=category, image=img)

        # Parent logic
        if is_parent:
            category.parent = None
        else:
            if not parent_id:
                messages.error(request, "You must select a parent category or mark as parent.")
                return redirect("store:edit_category", category_id=category.id)
            category.parent = Category.objects.get(id=parent_id)

        # Update slug if name changed
        if new_name != category.name:
            base_slug = slugify(new_name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(id=category.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            category.slug = slug

        category.save()
        messages.success(request, "Category updated successfully!")
        # ✅ Redirect to manage categories page instead of staying on edit page
        return redirect("store:manage_categories")

    return render(request, "store/edit_category.html", {"category": category, "categories": categories})



# Delete category
@admin_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, "Category deleted successfully!")
    return redirect("store:manage_categories")

# ------------------ PRODUCT CRUD ------------------

@admin_required
def manage_products(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, "store/manage_products.html", {"products": products})

@admin_required
def add_product(request):
    categories = Category.objects.all()
    sizes = [s[0] for s in SIZE_CHOICES]

    if request.method == "POST":
        name = request.POST.get("name")
        category_id = request.POST.get("category")
        description = request.POST.get("description")
        price = request.POST.get("price")
        discounted_price = request.POST.get("discounted_price") or None
        is_featured = "is_featured" in request.POST
        is_active = "is_active" in request.POST

        # Generate unique slug
        slug_base = slugify(name)
        slug = slug_base
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f"{slug_base}-{counter}"
            counter += 1

        product = Product.objects.create(
            name=name,
            slug=slug,  # unique slug
            category_id=category_id,
            description=description,
            price=price,
            discounted_price=discounted_price,
            is_featured=is_featured,
            is_active=is_active
        )

        # Save variants for each size
        for size in sizes:
            stock = request.POST.get(f"stock_{size}")
            active = f"active_{size}" in request.POST
            if stock:
                ProductVariant.objects.create(
                    product=product,
                    sku=f"{product.name[:3].upper()}-{size}-{product.id}",
                    size=size,
                    color="Default",
                    stock=int(stock),
                    is_active=active,
                )

        # Save images
        files = request.FILES.getlist("images")
        primary_index = int(request.POST.get("primary_image", 0))
        for idx, f in enumerate(files):
            ProductImage.objects.create(
                product=product,
                image=f,
                is_primary=(idx == primary_index)
            )

        messages.success(request, "Product added successfully!")
        return redirect("store:manage_products")

    return render(request, "store/add_product.html", {"categories": categories, "sizes": sizes})

@admin_required
def edit_product(request, product_id):
    product = Product.objects.get(id=product_id)
    categories = Category.objects.all()
    sizes = [s[0] for s in SIZE_CHOICES]

    # Prepare size_variants
    size_variants = []
    variants_dict = {v.size: v for v in product.variants.all()}
    for size in sizes:
        size_variants.append((size, variants_dict.get(size)))

    images = product.images.all()

    if request.method == "POST":
        new_name = request.POST.get("name")
        if product.name != new_name:
            product.slug = generate_unique_slug(new_name, product_id=product.id)

        product.name = new_name
        product.category_id = request.POST.get("category")
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")
        product.discounted_price = request.POST.get("discounted_price") or None
        product.is_featured = "is_featured" in request.POST
        product.is_active = "is_active" in request.POST
        product.save()

        # Update or create variants
        for size, variant in size_variants:
            stock = request.POST.get(f"stock_{size}")
            active = f"active_{size}" in request.POST
            if stock:
                if variant:
                    variant.stock = int(stock)
                    variant.is_active = active
                    variant.save()
                else:
                    ProductVariant.objects.create(
                        product=product,
                        sku=f"{product.name[:3].upper()}-{size}-{product.id}",
                        size=size,
                        color="Default",
                        stock=int(stock),
                        is_active=active,
                    )

        # Update primary existing image
        primary_existing = request.POST.get("primary_existing")
        if primary_existing:
            for img in images:
                img.is_primary = str(img.id) == primary_existing
                img.save()

        # Add new images
        files = request.FILES.getlist("images")
        primary_new_index = int(request.POST.get("primary_new", -1))
        for idx, f in enumerate(files):
            ProductImage.objects.create(
                product=product,
                image=f,
                is_primary=(idx == primary_new_index)
            )

        messages.success(request, "Product updated successfully!")
        return redirect("store:manage_products")

    return render(request, "store/edit_product.html", {
        "product": product,
        "categories": categories,
        "size_variants": size_variants,
        "images": images
    })


@admin_required
def delete_product_image(request, image_id):
    img = get_object_or_404(ProductImage, id=image_id)
    product_id = img.product.id
    img.delete()
    messages.success(request, "Image deleted successfully!")
    return redirect("store:edit_product", product_id=product_id)

@admin_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect("store:manage_products")

# ------------------ PRODUCT VARIANT CRUD ------------------

@admin_required
def manage_variants(request):
    variants = ProductVariant.objects.all()
    return render(request, "store/manage_variants.html", {"variants": variants})

@admin_required
def add_variant(request):
    products = Product.objects.filter(is_active=True)
    if request.method == "POST":
        product_id = request.POST.get("product")
        sku = request.POST.get("sku")
        size = request.POST.get("size")
        color = request.POST.get("color")
        price = request.POST.get("price") or None
        stock = int(request.POST.get("stock", 0))
        is_active = "is_active" in request.POST

        ProductVariant.objects.create(
            product_id=product_id,
            sku=sku,
            size=size,
            color=color,
            price=Decimal(price) if price else None,
            stock=stock,
            is_active=is_active
        )
        messages.success(request, "Product variant added successfully!")
        return redirect("store:manage_variants")

    return render(request, "store/add_variant.html", {"products": products, "sizes": SIZE_CHOICES})

@admin_required
def edit_variant(request, pk):
    variant = get_object_or_404(ProductVariant, pk=pk)
    products = Product.objects.filter(is_active=True)
    if request.method == "POST":
        variant.product_id = request.POST.get("product")
        variant.sku = request.POST.get("sku")
        variant.size = request.POST.get("size")
        variant.color = request.POST.get("color")
        price = request.POST.get("price") or None
        variant.price = Decimal(price) if price else None
        variant.stock = int(request.POST.get("stock", 0))
        variant.is_active = "is_active" in request.POST
        variant.save()
        messages.success(request, "Variant updated successfully!")
        return redirect("store:manage_variants")

    return render(request, "store/edit_variant.html", {"variant": variant, "products": products, "sizes": SIZE_CHOICES})

@admin_required
def delete_variant(request, pk):
    variant = get_object_or_404(ProductVariant, pk=pk)
    variant.delete()
    messages.success(request, "Variant deleted successfully.")
    return redirect("store:manage_variants")

# ------------------ PRODUCT IMAGE CRUD ------------------

@admin_required
def manage_images(request):
    images = ProductImage.objects.all()
    return render(request, "store/manage_images.html", {"images": images})

@admin_required
def add_image(request):
    if request.method == "POST":
        form = ProductImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Image added successfully.")
            return redirect("store:manage_images")
    else:
        form = ProductImageForm()
    return render(request, "store/add_image.html", {"form": form})

@admin_required
def edit_image(request, pk):
    image = get_object_or_404(ProductImage, pk=pk)
    if request.method == "POST":
        form = ProductImageForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            form.save()
            messages.success(request, "Image updated successfully.")
            return redirect("store:manage_images")
    else:
        form = ProductImageForm(instance=image)
    return render(request, "store/edit_image.html", {"form": form})

@admin_required
def delete_image(request, pk):
    image = get_object_or_404(ProductImage, pk=pk)
    image.delete()
    messages.success(request, "Image deleted successfully.")
    return redirect("store:manage_images")

# ------------------ COUPON CRUD ------------------

@admin_required
def manage_coupons(request):
    coupons = Coupon.objects.all()
    return render(request, "store/manage_coupons.html", {"coupons": coupons})

@admin_required
def add_coupon(request):
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon added successfully.")
            return redirect("store:manage_coupons")
    else:
        form = CouponForm()
    return render(request, "store/add_coupon.html", {"form": form})

@admin_required
def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == "POST":
        coupon.code = request.POST.get("code")
        coupon.discount_percent = request.POST.get("discount_percent")
        coupon.min_amount = request.POST.get("min_amount")
        coupon.start_date = request.POST.get("start_date")
        coupon.end_date = request.POST.get("end_date")
        coupon.active = "active" in request.POST
        coupon.save()
        messages.success(request, "Coupon updated successfully!")
        return redirect("store:manage_coupons")
    return render(request, "store/edit_coupon.html", {"coupon": coupon})

@admin_required
def delete_coupon(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    messages.success(request, "Coupon deleted successfully.")
    return redirect("store:manage_coupons")


