# outfits/views.py
import logging
import json
from decimal import Decimal
from datetime import date, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth import login, get_user_model
from django.utils import timezone

from .models import Outfit, Category, Order, OrderItem, UserProfile
from .forms import (
    CheckoutForm, CartAddItemForm, CustomUserCreationForm,
    OutfitForm, PaymentSlipUploadForm, UserEditForm, UserProfileForm,
    ReturnUploadForm
)

logger = logging.getLogger(__name__)

# ---------- Core Views ----------

def home(request):
    """Displays the homepage with featured outfits and categories."""
    featured_outfits = Outfit.objects.filter(is_active=True).order_by('?')[:6] # Get 6 random active outfits
    categories = Category.objects.all()
    cart = request.session.get(settings.CART_SESSION_ID, {})
    cart_outfit_ids = list(cart.keys()) # Pass IDs for checking in template
    context = {
        'featured_outfits': featured_outfits,
        'categories': categories,
        'cart_outfit_ids': cart_outfit_ids
    }
    return render(request, 'outfits/home.html', context)

def register_view(request):
    """Handles user registration."""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Log the user in automatically after registration
            messages.success(request, "Registration successful! Welcome.")
            return redirect(settings.LOGIN_REDIRECT_URL)
        else:
            # Add specific error messages if possible, otherwise generic
            error_message = "Please correct the errors below."
            messages.error(request, error_message)
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

# ---------- Outfit Listing & Detail Views ----------

class OutfitListView(ListView):
    """Displays all active outfits, paginated."""
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        # Optimize query by selecting related category
        return Outfit.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['title'] = "All Outfits"
        cart = self.request.session.get(settings.CART_SESSION_ID, {})
        context['cart_outfit_ids'] = list(cart.keys()) # For "Add to Cart" button state
        return context

class OutfitByCategoryListView(ListView):
    """Displays outfits filtered by category, paginated."""
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        # Get category object or raise 404 if not found
        self.category = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        # Filter outfits by the found category and optimize query
        return Outfit.objects.filter(category=self.category, is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category # Pass category to template
        context['categories'] = Category.objects.all() # For potential sidebar/filter display
        context['title'] = f"Category: {self.category.name}"
        cart = self.request.session.get(settings.CART_SESSION_ID, {})
        context['cart_outfit_ids'] = list(cart.keys())
        return context

class OutfitDetailView(DetailView):
    """Displays details for a single active outfit."""
    model = Outfit
    template_name = 'outfits/detail.html'
    context_object_name = 'outfit'

    def get_queryset(self):
        # Only show active outfits and optimize query
        return Outfit.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['add_to_cart_form'] = CartAddItemForm() # Form is simple, not really needed here

        # Get related outfits (same category, excluding self)
        if self.object.category:
            context['related_outfits'] = Outfit.objects.filter(
                category=self.object.category,
                is_active=True
            ).exclude(pk=self.object.pk).select_related('category')[:4] # Limit to 4 related items

        # Check cart status
        cart = self.request.session.get(settings.CART_SESSION_ID, {})
        context['cart_outfit_ids'] = list(cart.keys())

        # Check current availability status (for display)
        try:
            # Check availability for today (or a default relevant date range)
            today = timezone.now().date()
            is_currently_available = self.object.is_available(today, today)
            context['current_status_text'] = "Available" if is_currently_available else "Currently Rented"
        except Exception as e:
            logger.error(f"Error checking availability for outfit {self.object.pk}: {e}")
            context['current_status_text'] = "Availability Check Error" # Inform user

        return context

class OutfitSearchView(ListView):
    """Handles searching for outfits."""
    model = Outfit
    template_name = 'outfits/list.html' # Reuse the list template
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        self.query = query # Store query for context
        if query:
            # Search in name, description, and category name (case-insensitive)
            return Outfit.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query),
                is_active=True
            ).select_related('category').distinct() # Use distinct to avoid duplicates if multiple criteria match
        return Outfit.objects.none() # Return empty if no query

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.query
        context['categories'] = Category.objects.all()
        context['title'] = f"Search Results for '{self.query}'" if self.query else "Search Outfits"
        cart = self.request.session.get(settings.CART_SESSION_ID, {})
        context['cart_outfit_ids'] = list(cart.keys())
        return context

# ---------- Cart Views ----------

def get_cart_items_and_total(request):
    """Helper function to get processed cart items and subtotal."""
    cart_session = request.session.get(settings.CART_SESSION_ID, {})
    cart_items_data = []
    cart_subtotal_per_day = Decimal('0.00')
    outfit_ids = list(cart_session.keys())

    # Fetch outfits in one query
    outfits_in_cart = {str(o.id): o for o in Outfit.objects.filter(id__in=outfit_ids, is_active=True)}

    valid_cart_session = {} # Build a new session dict with only valid items
    ids_to_remove = []

    for outfit_id_str in outfit_ids:
        item_data = cart_session[outfit_id_str]
        outfit = outfits_in_cart.get(outfit_id_str)

        if outfit:
            # Current logic assumes quantity is always 1 for rentals per item type
            quantity = 1 # item_data.get('quantity', 1) # Use 1 for now
            price_per_day = outfit.price
            item_subtotal = price_per_day * quantity
            cart_subtotal_per_day += item_subtotal
            cart_items_data.append({
                'outfit': outfit,
                'quantity': quantity,
                'price_per_day': price_per_day,
                'item_subtotal': item_subtotal
            })
            valid_cart_session[outfit_id_str] = {'quantity': quantity} # Add valid item to new session data
        else:
            # Mark ID for removal if outfit not found or inactive
            ids_to_remove.append(outfit_id_str)

    # Update session only if changes were made (invalid items removed)
    session_changed = False
    if ids_to_remove:
        # Create the final valid cart by filtering out removed IDs (less efficient than building new)
        # valid_cart_session = {k: v for k, v in cart_session.items() if k not in ids_to_remove}
        session_changed = True
        logger.info(f"Removing invalid outfit IDs from cart: {ids_to_remove}")

    # If the structure or content of the cart in session needs updating
    if session_changed or set(valid_cart_session.keys()) != set(cart_session.keys()):
         request.session[settings.CART_SESSION_ID] = valid_cart_session
         request.session.modified = True

    return cart_items_data, cart_subtotal_per_day

def cart_detail(request):
    """Displays the contents of the shopping cart."""
    cart_items, cart_subtotal_per_day = get_cart_items_and_total(request)
    context = {
        'cart_items': cart_items,
        'cart_subtotal_per_day': cart_subtotal_per_day
    }
    return render(request, 'outfits/cart_detail.html', context)

@require_POST # Ensure only POST requests can add items
def add_to_cart(request, outfit_id):
    """Adds an outfit to the cart."""
    outfit = get_object_or_404(Outfit, id=outfit_id, is_active=True)
    cart = request.session.get(settings.CART_SESSION_ID, {})
    outfit_key = str(outfit_id) # Session keys must be strings

    # Current logic: Only allow one of each outfit type in cart
    if outfit_key in cart:
        messages.warning(request, f"'{outfit.name}' is already in your cart.")
    else:
        cart[outfit_key] = {'quantity': 1} # Add item with quantity 1
        request.session[settings.CART_SESSION_ID] = cart
        request.session.modified = True # Mark session as modified
        messages.success(request, f"Added '{outfit.name}' to your cart.")

    # Redirect back to the previous page or cart
    redirect_url = request.POST.get('next', reverse('outfits:cart_detail'))
    return redirect(redirect_url)

@require_POST # Ensure only POST requests can remove items
def remove_from_cart(request, outfit_id):
    """Removes an outfit from the cart."""
    cart = request.session.get(settings.CART_SESSION_ID, {})
    outfit_key = str(outfit_id)

    if outfit_key in cart:
        # Try to get outfit name for message, handle if outfit deleted
        try:
            outfit_name = Outfit.objects.get(id=outfit_id).name
        except Outfit.DoesNotExist:
            outfit_name = f"Item ID {outfit_id}"

        del cart[outfit_key] # Remove the item
        request.session[settings.CART_SESSION_ID] = cart
        request.session.modified = True
        messages.success(request, f"Removed '{outfit_name}' from your cart.")
    else:
        messages.warning(request, "Item not found in your cart.")

    return redirect('outfits:cart_detail')

# ---------- Checkout & Payment Views ----------

@login_required # User must be logged in to checkout
def checkout_view(request):
    """Handles the checkout process: collecting user info and creating an order."""
    cart_items, cart_subtotal_per_day = get_cart_items_and_total(request)

    # If cart is empty, redirect
    if not cart_items:
        messages.warning(request, "Your cart is empty. Please add items before checking out.")
        return redirect('outfits:outfit-list')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['rental_start_date']
            end_date = form.cleaned_data['rental_end_date']

            # --- Availability Check ---
            unavailable_items = []
            for item_data in cart_items:
                if not item_data['outfit'].is_available(start_date, end_date, quantity=item_data['quantity']):
                    unavailable_items.append(item_data['outfit'].name)

            if unavailable_items:
                messages.error(request, f"Sorry, the following items are not available for the selected dates: {', '.join(unavailable_items)}. Please adjust dates or remove items.")
                # Re-render form with error
                context = {'form': form, 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day}
                return render(request, 'outfits/checkout.html', context)
            # --- End Availability Check ---

            try:
                # Use a transaction to ensure all steps succeed or fail together
                with transaction.atomic():
                    # Create the Order object
                    order = Order(
                        user=request.user,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone'],
                        address=form.cleaned_data['address'],
                        rental_start_date=start_date,
                        rental_end_date=end_date,
                        status='pending', # Initial status
                        payment_method='Bank Transfer' # Default method
                        # shipping_cost will be calculated or set later
                    )
                    order.save() # Save order first to get an ID

                    # Create OrderItem objects for each item in the cart
                    order_items_to_create = []
                    for item_data in cart_items:
                        order_items_to_create.append(OrderItem(
                            order=order,
                            outfit=item_data['outfit'],
                            quantity=item_data['quantity'], # Should be 1 based on current cart logic
                            price_per_day=item_data['outfit'].price # Store price at time of order
                        ))
                    OrderItem.objects.bulk_create(order_items_to_create)

                    # Recalculate and save the total amount on the order
                    # Fetch order again to ensure related items are accessible for calculation
                    order_from_db = Order.objects.get(pk=order.pk)
                    order_from_db.total_amount = order_from_db.calculate_total_amount()
                    # Add logic here to calculate/set shipping_cost if needed before final save
                    # order_from_db.shipping_cost = calculate_shipping(order_from_db.address)
                    order_from_db.total_amount += order_from_db.shipping_cost # Ensure total includes shipping
                    order_from_db.save()

                    # Clear the cart from session
                    del request.session[settings.CART_SESSION_ID]
                    request.session.modified = True
                    # Store order ID for payment page redirect
                    request.session['latest_order_id'] = order_from_db.id

                    # Redirect to payment processing page
                    return redirect('outfits:payment_process', order_id=order_from_db.id)

            except Exception as e:
                 # Catch any unexpected errors during order creation
                 logger.error(f"Error creating order for user {request.user.id}: {e}", exc_info=True)
                 messages.error(request, f"An unexpected error occurred while creating your order. Please try again. Error: {e}")
                 # Re-render form
                 context = {'form': form, 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day}
                 return render(request, 'outfits/checkout.html', context)
        else:
             # Form validation failed
             messages.error(request, "Please correct the errors in the form below.")
             context = {'form': form, 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day}
             return render(request, 'outfits/checkout.html', context)

    else: # GET request
        # Pre-fill form with user data if available
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
            # Try to get phone/address from profile
            try:
                profile = request.user.profile # Assumes related_name='profile'
                if profile.phone: initial_data['phone'] = profile.phone
                if profile.address: initial_data['address'] = profile.address
            except UserProfile.DoesNotExist:
                logger.info(f"UserProfile not found for user {request.user.id}, creating one.")
                UserProfile.objects.create(user=request.user) # Create profile if missing
            except AttributeError:
                # Handle cases where user object might not have 'profile' yet
                logger.warning(f"User {request.user.id} has no 'profile' attribute yet.")
                UserProfile.objects.get_or_create(user=request.user) # Ensure profile exists

        form = CheckoutForm(initial=initial_data)
        context = {'form': form, 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day}
        return render(request, 'outfits/checkout.html', context)

@login_required
def payment_process_view(request, order_id):
    """Handles the submission of payment proof (slip upload)."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    form = None # Initialize form

    # Only allow submission if order is pending payment
    if order.status == 'pending':
        if request.method == 'POST':
            form = PaymentSlipUploadForm(request.POST, request.FILES, instance=order)
            if form.is_valid():
                try:
                    # Save form data (payment_datetime, payment_slip) to the order
                    updated_order = form.save(commit=False)
                    updated_order.status = 'waiting_for_approval' # Update status
                    updated_order.save()
                    messages.success(request, f"Payment proof for Order #{order.id} submitted successfully. Awaiting approval.")
                    return redirect('outfits:order_detail', order_id=order.id) # Redirect to order details
                except Exception as e:
                    logger.error(f"Error saving payment slip for order {order.id}: {e}", exc_info=True)
                    messages.error(request, "An error occurred while saving your payment information.")
            else:
                # Form is invalid
                messages.error(request, "Please correct the errors and upload a valid slip.")
        else: # GET request
            form = PaymentSlipUploadForm() # Show an empty form

    # Handle cases where payment shouldn't be processed
    elif order.status == 'waiting_for_approval':
        messages.info(request, f"Order #{order.id} is already awaiting payment approval.")
    elif order.status == 'failed':
        messages.error(request, f"Payment for Order #{order.id} failed previously. Reason: {order.admin_payment_note or 'Not specified'}. Please contact support if needed.")
    else: # Other statuses (processing, shipped, etc.)
        messages.info(request, f"Payment cannot be submitted for Order #{order.id} (Status: {order.get_status_display()}).")

    # Prepare bank details for display
    bank_details = {
        'account_name': settings.BANK_ACCOUNT_NAME,
        'account_number': settings.BANK_ACCOUNT_NUMBER,
        'bank_name': settings.BANK_NAME,
        'qr_code_path': settings.BANK_QR_CODE_STATIC_PATH if settings.BANK_QR_CODE_STATIC_PATH else None
    }
    context = {'order': order, 'form': form, 'bank_details': bank_details}
    return render(request, 'outfits/payment_process.html', context)

@login_required
def payment_result_view(request):
    """Displays a generic payment result/status page, often after redirection."""
    # Try to get the most recent order ID from session if available
    order_id = request.session.get('latest_order_id')
    order = None
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            # Optional: Clear the session variable after use
            # del request.session['latest_order_id']
            # request.session.modified = True
        except Order.DoesNotExist:
            logger.warning(f"Order ID {order_id} from session not found for user {request.user.id}")
            pass # Order not found or doesn't belong to user

    # Display appropriate messages based on order status (or generic message if no order)
    if order:
         # Add more specific messages based on status transitions if needed
         if order.status == 'waiting_for_approval':
             messages.info(request, f"Payment proof for Order #{order.id} submitted. Awaiting approval.")
         elif order.status == 'processing':
             messages.success(request, f"Payment for Order #{order.id} confirmed and is being processed.")
         elif order.status == 'failed':
              messages.error(request, f"Payment for Order #{order.id} failed or was rejected.")
         # Add messages for other relevant statuses if needed
         else:
              messages.info(request, f"Current status for Order #{order.id}: {order.get_status_display()}.")
    else:
        # Generic message if no specific order context
        messages.info(request, "Welcome to MindVibe!") # Or redirect to history

    return render(request, 'outfits/payment_result.html', {'order': order})

# ---------- Order History & Detail Views ----------

@login_required
def order_history_view(request):
    """Displays the user's past and current orders."""
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items', 'items__outfit' # Optimize query by prefetching related items and outfits
    ).order_by('-created_at') # Show newest orders first
    return render(request, 'outfits/order_history.html', {'orders': orders})

@login_required
def order_detail_view(request, order_id):
    """Displays details for a specific order belonging to the user."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items', 'items__outfit'), # Optimize query
        id=order_id,
        user=request.user # Ensure user can only see their own orders
    )
    context = {'order': order}
    return render(request, 'outfits/order_detail.html', context)

# ---------- User Profile & Return Views ----------

@login_required
def user_profile_view(request):
    """Allows users to view and edit their profile information."""
    user = request.user
    # Get or create the profile associated with the user
    profile, created = UserProfile.objects.get_or_create(user=user)
    if created:
        logger.info(f"Created UserProfile for user {user.id}")

    if request.method == 'POST':
        # Populate forms with POST data and existing instances
        user_form = UserEditForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('outfits:user_profile') # Redirect back to profile page
        else:
            messages.error(request, 'Please correct the errors below.')
    else: # GET request
        # Populate forms with existing instances
        user_form = UserEditForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'outfits/user_profile.html', context)


@login_required
def initiate_return_view(request, order_id):
    """Handles the submission of return information (tracking, slip)."""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Define statuses where return is allowed
    allowed_statuses_for_return = ['rented', 'shipped'] # Adjust as needed

    # Check if return is allowed based on current status
    if order.status not in allowed_statuses_for_return:
        messages.error(request, f"Cannot initiate return for Order #{order.id} with status '{order.get_status_display()}'.")
        return redirect('outfits:order_detail', order_id=order.id)

    # Check if return info has already been submitted
    if order.return_tracking_number or order.return_slip:
         messages.warning(request, f"Return information for Order #{order.id} has already been submitted.")
         return redirect('outfits:order_detail', order_id=order.id)

    if request.method == 'POST':
        form = ReturnUploadForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            try:
                return_info = form.save(commit=False)
                return_info.status = 'return_shipped' # Update order status
                return_info.return_initiated_at = timezone.now() # Record submission time
                return_info.save()
                messages.success(request, f"Return information for Order #{order.id} submitted successfully.")
                return redirect('outfits:order_detail', order_id=order.id)
            except Exception as e:
                 logger.error(f"Error saving return info for order {order.id}: {e}", exc_info=True)
                 messages.error(request, "An error occurred while saving return information.")
        else:
             messages.error(request, "Please correct the errors and provide valid return details.")
    else: # GET request
         # Show empty form (or potentially pre-fill tracking if saved partially before?)
         form = ReturnUploadForm(instance=order)

    context = { 'order': order, 'form': form, }
    return render(request, 'outfits/initiate_return.html', context)