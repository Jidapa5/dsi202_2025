from django.db import models
from django.conf import settings  # Added

class Outfit(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='outfits/', null=True, blank=True)
    price = models.FloatField(default=0.0)
    is_rented = models.BooleanField(default=False)
    size = models.CharField(max_length=20, blank=True, null=True)  # Added
    material = models.CharField(max_length=100, blank=True, null=True)  # Added

    def __str__(self):
        return self.name

class Rental(models.Model):  # Added
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    outfit = models.ForeignKey(Outfit, on_delete=models.CASCADE)
    rental_date = models.DateField(auto_now_add=True)
    duration = models.IntegerField()
    total_price = models.FloatField()
    payment_slip = models.ImageField(upload_to='payment_slips/', null=True, blank=True)  # เพิ่ม Field นี้
    payment_date = models.DateField(null=True, blank=True)  # เพิ่ม Field นี้
    is_paid = models.BooleanField(default=False)  # เพิ่ม Field นี้

    def __str__(self):
        return f"{self.user.username} rents {self.outfit.name}"