def cart(request):
    cart_data = request.session.get('cart', {})
    cart_item_count = sum(item['quantity'] for item in cart_data.values())
    return {'cart_item_count': cart_item_count}
