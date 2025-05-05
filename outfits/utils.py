def calculate_cart_total(cart):
    total = 0
    for item in cart.values():
        total += item['quantity'] * float(item.get('price', 0))
    return total
