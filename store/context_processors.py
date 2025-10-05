# store/context_processors.py
from .models import CartItem, Wishlist

def cart_and_wishlist_counts(request):
    cart_count = 0
    wishlist_count = 0

    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).count()
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
    else:
        session_key = request.session.session_key or request.session.create()
        cart_count = CartItem.objects.filter(session_key=session_key).count()

    return {
        "cart_count": cart_count,
        "wishlist_count": wishlist_count,
    }
