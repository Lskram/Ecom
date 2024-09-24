from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Category, Product, Cart, CartItem, Order, OrderItem
from django.shortcuts import render, redirect
from .models import Cart, Order, OrderItem
from .forms import OrderCreateForm

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    
    return render(request,
                  'store/product/list.html',
                  {'category': category,
                   'categories': categories,
                   'products': products})

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    return render(request,
                  'store/product/detail.html',
                  {'product': product})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('product_list')

@login_required
def view_cart(request):
    cart = Cart.objects.filter(user=request.user).first()
    items = CartItem.objects.filter(cart=cart) if cart else []
    total = sum(item.product.price * item.quantity for item in items)
    return render(request, 'store/cart.html', {'items': items, 'total': total})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.stock > 0:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
        product.stock -= 1
        product.save()
        messages.success(request, f"{product.name} added to your cart.")
    else:
        messages.error(request, f"Sorry, {product.name} is out of stock.")
    return redirect('product_list')

@login_required
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity'))
        if quantity > 0:
            item.quantity = quantity
            item.save()
        else:
            item.delete()
    return redirect('view_cart')

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    if request.method == 'POST':
        # Process the order
        order = Order.objects.create(user=request.user, total_price=cart.get_total_price())
        for item in cart.items.all():
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)
        cart.items.all().delete()
        return redirect('order_confirmation', order_id=order.id)
    return render(request, 'store/checkout.html', {'cart': cart})

@login_required
def order_create(request):
    cart = Cart.objects.get(user=request.user)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total_price = cart.get_total_price()
            order.save()
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.product.price,
                    quantity=item.quantity
                )
            cart.clear()  # Clear the cart after order is created
            return render(request, 'store/order_created.html', {'order': order})
    else:
        form = OrderCreateForm()
    return render(request, 'store/order_create.html', {'cart': cart, 'form': form})