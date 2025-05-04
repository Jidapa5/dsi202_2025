# outfits/context_processors.py

def cart_context(request):
    # ใส่ข้อมูลที่ต้องการใช้ในทุกๆ template ที่เกี่ยวกับ cart
    # ตัวอย่างเช่น จำนวนสินค้าในตะกร้า
    cart = request.session.get('cart', [])
    return {'cart_count': len(cart)}
