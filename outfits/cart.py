from decimal import Decimal
from django.conf import settings
from .models import Outfit

class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, outfit, duration_days=1, update_duration=False):
        """
        Add an outfit to the cart or update its duration.
        """
        outfit_id = str(outfit.id)
        if outfit_id not in self.cart:
            self.cart[outfit_id] = {'duration_days': 0,
                                      'price': str(outfit.price)} # Store price as string

        if update_duration:
            self.cart[outfit_id]['duration_days'] = int(duration_days)
        else:
             # ถ้า Add ซ้ำ ควรทำอย่างไร? ตอนนี้แค่ set duration ใหม่
             self.cart[outfit_id]['duration_days'] = int(duration_days)

        if self.cart[outfit_id]['duration_days'] <= 0:
             self.remove(outfit) # ลบถ้า duration <= 0
        else:
            self.save()


    def save(self):
        # mark the session as "modified" to make sure it gets saved
        self.session.modified = True

    def remove(self, outfit):
        """
        Remove an outfit from the cart.
        """
        outfit_id = str(outfit.id)
        if outfit_id in self.cart:
            del self.cart[outfit_id]
            self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the outfits
        from the database.
        """
        outfit_ids = self.cart.keys()
        # get the outfit objects and add them to the cart
        outfits = Outfit.objects.filter(id__in=outfit_ids)
        cart = self.cart.copy()
        for outfit in outfits:
            cart[str(outfit.id)]['outfit'] = outfit
        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['duration_days']
            yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return len(self.cart)
        # หรือนับจาก duration_days? return sum(item['duration_days'] for item in self.cart.values())


    def get_total_price(self):
        return sum(Decimal(item['price']) * item['duration_days'] for item in self.cart.values())

    def clear(self):
        # remove cart from session
        del self.session[settings.CART_SESSION_ID]
        self.save()