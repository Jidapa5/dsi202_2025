# outfits/models.py
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Q
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Category Name")
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="Used for URL (auto-generated if blank)")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ('name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# --- Outfit Model ---
class Outfit(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='outfits', verbose_name="Category")
    name = models.CharField(max_length=100, verbose_name="Outfit Name")
    description = models.TextField(verbose_name="Description")
    image = models.ImageField(upload_to='outfits/', null=True, blank=True, verbose_name="Image")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Rental Price per Day")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        verbose_name = "Outfit"
        verbose_name_plural = "Outfits"
        ordering = ('name',)

    def __str__(self):
        return self.name

    def is_available(self, start_date, end_date, quantity=1):
        """Checks if the outfit is available for the given dates."""
        if not start_date or not end_date or start_date > end_date or quantity < 1:
            return False

        relevant_statuses = ['pending', 'waiting_for_approval', 'processing', 'shipped', 'rented']

        # Find overlapping order items for this specific outfit
        # This query looks for any OrderItem associated with this Outfit where its Order
        # falls within the relevant statuses and the rental period overlaps with the requested dates.
        overlapping_items = self.order_items.filter(
            order__status__in=relevant_statuses,
            order__rental_start_date__lte=end_date, # Booking starts on or before the requested end_date
            order__rental_end_date__gte=start_date  # Booking ends on or after the requested start_date
        )
        
        # If any such overlapping booking exists, the outfit is not available.
        # This assumes each outfit instance is unique (stock of 1).
        # If you had multiple units of the same outfit, you'd need to sum quantities.
        return not overlapping_items.exists()

    # Removed get_upcoming_bookings(self) method

# --- Order Model ---
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Payment'),
        ('waiting_for_approval', 'Awaiting Approval'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('rented', 'Rented'),
        ('return_shipped', 'Return Shipped'), 
        ('return_received', 'Return Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Payment Failed/Invalid'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="User")
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    address = models.TextField(verbose_name="Shipping Address")
    rental_start_date = models.DateField(verbose_name="Rental Start Date", null=True, blank=True)
    rental_end_date = models.DateField(verbose_name="Rental End Date", null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Amount")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    paid = models.BooleanField(default=False, verbose_name="Payment Confirmed")
    payment_method = models.CharField(max_length=50, default='Bank Transfer', editable=False, verbose_name="Payment Method")
    payment_slip = models.ImageField(upload_to='payment_slips/%Y/%m/', blank=True, null=True, verbose_name="Payment Slip")
    payment_datetime = models.DateTimeField(blank=True, null=True, verbose_name="Payment Date/Time (Reported)")
    admin_payment_note = models.TextField(blank=True, verbose_name="Admin Payment Note")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Shipping Cost")
    shipping_tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping Tracking No.")
    return_tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Return Tracking No.")
    return_slip = models.ImageField(
        upload_to='return_slips/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Return Slip/Photo"
    )
    return_initiated_at = models.DateTimeField( 
        blank=True,
        null=True,
        verbose_name="Return Initiated At"
    )

    class Meta:
        verbose_name = "Rental Order"
        verbose_name_plural = "Rental Orders"
        ordering = ('-created_at',)

    def __str__(self):
        return f"Order #{self.id} ({self.first_name} {self.last_name})"

    @property
    def rental_duration_days(self):
        if self.rental_start_date and self.rental_end_date and self.rental_end_date >= self.rental_start_date:
            return (self.rental_end_date - self.rental_start_date).days + 1
        return 0

    def calculate_items_total(self):
        total = Decimal('0.00')
        duration = self.rental_duration_days
        if duration > 0 and self.pk: 
            for item in self.items.all():
                if item.price_per_day is not None:
                    total += item.price_per_day * duration * item.quantity
        return total

    def calculate_total_amount(self):
        items_total = self.calculate_items_total()
        grand_total = items_total + self.shipping_cost 
        return grand_total

    def clean(self):
        if self.rental_start_date and self.rental_end_date:
            if self.rental_end_date < self.rental_start_date:
                raise ValidationError("Rental end date cannot be before the start date.")
        elif self.rental_start_date or self.rental_end_date:
             if not (self.rental_start_date and self.rental_end_date):
                 pass

# --- OrderItem Model ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="Rental Order")
    outfit = models.ForeignKey(Outfit, related_name='order_items', on_delete=models.PROTECT, verbose_name="Outfit") 
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price per Day (at time of order)", null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity") 

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity} x {self.outfit.name} (Order #{self.order.id})"

    @property
    def item_total_cost(self):
        if hasattr(self, 'order') and self.order: 
             duration = self.order.rental_duration_days
             if self.price_per_day is not None and duration > 0:
                 return self.price_per_day * duration * self.quantity
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        if not self.pk and self.outfit and self.price_per_day is None:
            self.price_per_day = self.outfit.price
        super().save(*args, **kwargs)

# --- UserProfile Model ---
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile', verbose_name="User")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Phone Number")
    address = models.TextField(blank=True, verbose_name="Saved Address") 

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile for {self.user.username}"

# --- Signal Receivers ---
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)