from django.db import models

class Outfit(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='outfits/', null=True, blank=True)
    price = models.FloatField(default=0.0)
    is_rented = models.BooleanField(default=False)

    def __str__(self):
        return self.name