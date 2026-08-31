from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PromoTheme(models.Model):
    """Allows stockkeepers to define celebration/promo names and custom UI color themes dynamically."""
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Christmas, Black Friday, Anniversary Sale")
    is_active = models.BooleanField(default=False, help_text="Check to activate this theme globally across the store interface.")
    background_color = models.CharField(max_length=50, default="#111111", help_text="Hex or CSS color for header/background theme (e.g. #cc0001)")
    accent_color = models.CharField(max_length=50, default="#ffc107", help_text="Hex or CSS color for badges/highlights")
    text_color = models.CharField(max_length=50, default="#ffffff", help_text="Hex or CSS color for text/write-ups under this theme")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = " [ACTIVE]" if self.is_active else ""
        return f"{self.name}{status}"


class StoreGlobalSetting(models.Model):
    """
    Controlled exclusively by the CEO. Allows dynamic adjustments of global
    store financial rules like partial payment activation thresholds and deposit percentages,
    as well as official company identity details for invoices.
    """
    partial_payment_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, default=20000.00,
        help_text="Minimum order total required to trigger partial payment option (default: ₦20,000)"
    )
    default_deposit_percentage = models.PositiveIntegerField(
        default=80,
        help_text="Global default deposit percentage required for large items (e.g., 80%)"
    )
    shipping_fee_below_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, default=3000.00,
        help_text="Flat shipping fee for orders below the threshold"
    )
    vat_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=7.50,
        help_text="Automated tax calculation rate (Default Nigerian VAT: 7.5%)"
    )
    
    # --- CEO-Managed Official Identity Fields for Invoices ---
    store_address = models.TextField(
        default="Port Harcourt, Nigeria",
        help_text="Official physical business address shown on invoices"
    )
    store_email = models.EmailField(
        default="support@technic.com.ng",
        help_text="Official business support email shown on invoices"
    )
    store_phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Official business contact phone number shown on invoices"
    )
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CEO Global Store Settings (VAT: {self.vat_percentage}%, Deposit: {self.default_deposit_percentage}%)"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class RefundReason(models.Model):
    """Managed dynamically by the CEO to provide dropdown choices for customer refund requests."""
    reason_text = models.CharField(max_length=255, unique=True, help_text="Reason description selectable by customers during a return/refund")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reason_text

class UserSearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    keyword = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.keyword} ({self.user or self.session_key})"

class UserAddressBook(models.Model):
    """Customer saved delivery locations with Nigerian States, LGAs, Street Address, and Phone numbers."""
    
    NIGERIAN_STATES_CHOICES = (
        ('Abia', 'Abia'), ('Adamawa', 'Adamawa'), ('Akwa Ibom', 'Akwa Ibom'), ('Anambra', 'Anambra'),
        ('Bauchi', 'Bauchi'), ('Bayelsa', 'Bayelsa'), ('Benue', 'Benue'), ('Borno', 'Borno'),
        ('Cross River', 'Cross River'), ('Delta', 'Delta'), ('Ebonyi', 'Ebonyi'), ('Edo', 'Edo'),
        ('Ekiti', 'Ekiti'), ('Enugu', 'Enugu'), ('Gombe', 'Gombe'), ('Imo', 'Imo'),
        ('Jigawa', 'Jigawa'), ('Kaduna', 'Kaduna'), ('Kano', 'Kano'), ('Katsina', 'Katsina'),
        ('Kebbi', 'Kebbi'), ('Kogi', 'Kogi'), ('Kwara', 'Kwara'), ('Lagos', 'Lagos'),
        ('Nasarawa', 'Nasarawa'), ('Niger', 'Niger'), ('Ogun', 'Ogun'), ('Ondo', 'Ondo'),
        ('Osun', 'Osun'), ('Oyo', 'Oyo'), ('Plateau', 'Plateau'), ('Rivers', 'Rivers'),
        ('Sokoto', 'Sokoto'), ('Taraba', 'Taraba'), ('Yobe', 'Yobe'), ('Zamfara', 'Zamfara'),
        ('FCT - Abuja', 'FCT - Abuja')
    )

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_addresses')
    state = models.CharField(max_length=50, choices=NIGERIAN_STATES_CHOICES)
    lga = models.CharField(max_length=100, help_text="Local Government Area (e.g. Ikeja, Eti-Osa)")
    street_address = models.TextField(help_text="Full street address and land marks")
    phone_number = models.CharField(max_length=20, help_text="Contact phone number for this delivery location")
    is_default = models.BooleanField(default=False, help_text="Set as default address for quick checkout")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        default_tag = " [DEFAULT]" if self.is_default else ""
        return f"{self.customer.username} - {self.street_address}, {self.lga}, {self.state}{default_tag}"

class Vendor(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    
    # Pricing fields
    price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Original Regular Price")
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Standard discounted price on normal days")
    
    # Confidential Vendor Price (Visible ONLY to Stock Keeper, Finance, General Manager & CEO)
    vendor_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Confidential warehouse vendor stock cost. Visible ONLY to Stock Keeper, Finance, General Manager & CEO."
    )
    
    # Promotional & Celebration Settings
    promo_theme = models.ForeignKey('PromoTheme', on_delete=models.SET_NULL, blank=True, null=True, related_name='promo_products', help_text="Optional celebration event association")
    promo_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Special promotional/celebration price")
    
    stock_quantity = models.PositiveIntegerField(default=0)
    
    # Primary Image & Confidential Tags / Photo Search Visual Tags
    image = models.ImageField(upload_to='store/products/', blank=True, null=True)
    visual_search_tag = models.CharField(max_length=255, blank=True, null=True, help_text="Keywords for photo/visual search indexing")
    internal_brand_tag = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Confidential Brand/Supplier Tag (Visible ONLY to CEO, General Manager, Manager, and Finance)"
    )
    
    # Billing & Partial Payment Settings (Managed by Finance / Storekeeper / CEO)
    allow_partial_payment = models.BooleanField(
        default=False, 
        help_text="Allow upfront deposit with remainder due upon delivery for qualifying orders."
    )
    partial_deposit_percentage = models.PositiveIntegerField(
        default=80, 
        help_text="Upfront percentage required if partial payment is enabled (e.g. 80)."
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def current_active_price(self):
        """
        Priority Hierarchy:
        1. Active Promo / Celebration Price (overrides everything)
        2. S-Mart / Discount Price (overrides regular base price)
        3. Regular Base Price (fallback)
        """
        if self.promo_price and self.promo_theme and self.promo_theme.is_active:
            return self.promo_price
        return self.discount_price if self.discount_price else self.price
    

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='store/products/gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductVideo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_videos')
    video_file = models.FileField(upload_to='store/products/videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video for {self.product.name}"


class StoreOrder(models.Model):
    STATUS_CHOICES = (
        ('pending_payment', 'Pending Payment'),
        ('partial_payment_submitted', 'Partial Payment Submitted'),
        ('partial_payment_confirmed', 'Partial Payment Confirmed by Finance'),
        ('full_payment_submitted', 'Full Balance / 100% Payment Submitted'),
        ('full_payment_confirmed', 'Full Payment Confirmed by Finance'),
        ('order_ready', 'Order Ready for Dispatch'),
        ('picked_up', 'Picked Up by Rider (Live Tracking Active)'),
        ('arrived_at_customer', 'Arrived at Customer Location (Rider Locked)'),
        ('balance_paid', 'Balance Paid by Customer'),
        ('delivered', 'Delivered (Snap & Confirm Closed)'),
        ('completed', 'Completed'),
        ('return_requested', 'Return/Replacement Requested'),
        ('returned_to_store', 'Arrived at Store for Inspection'),
        ('replaced', 'Item Replaced'),
    )

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store_orders')
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default='pending_payment')
    
    # Financial fields with threshold rules
    items_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Vendor Cost & Supplier Split Tracking
    vendor_cost_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Cost amount sent or owed to the vendor/supplier for items in this order."
    )
    
    # Payment tracking & Escrow segregation
    payment_type = models.CharField(
        max_length=20, 
        choices=(('full', 'Full 100% Payment'), ('partial', 'Partial Deposit')), 
        default='full'
    )
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_paid = models.BooleanField(default=False)
    
    # Delivery and Contact Details
    shipping_address = models.TextField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Assigned Rider & Live GPS Tracking
    assigned_rider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='rider_store_deliveries'
    )
    rider_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Rider Live Latitude")
    rider_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Rider Live Longitude")
    is_location_live = models.BooleanField(default=False, verbose_name="Is Rider Location Broadcasting Live")
    
    # Proofs & Inspection
    delivery_proof_photo = models.ImageField(upload_to='store/delivery_proofs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Store Order #{self.id} - {self.customer.username} ({self.get_status_display()})"

    def update_vendor_cost(self):
        """Automatically calculates total vendor cost from all associated order items."""
        total_cost = sum((item.vendor_unit_price * item.quantity) for item in self.items.all())
        self.vendor_cost_amount = Decimal(str(total_cost)).quantize(Decimal('0.01'))
        self.save(update_fields=['vendor_cost_amount'])

    # --- Automated Tax & Financial Engine Helper Properties ---
    @property
    def computed_tax_dues(self):
        """Automatically calculates the Nigerian VAT (default 7.5%) on the items subtotal."""
        settings_obj = StoreGlobalSetting.get_settings()
        rate = settings_obj.vat_percentage / Decimal('100.00')
        return (self.items_subtotal * rate).quantize(Decimal('0.01'))

    @property
    def net_store_revenue(self):
        """Calculates store revenue after subtracting the vendor/supplier cost from the total amount."""
        cost = self.vendor_cost_amount or Decimal('0.00')
        return (self.total_amount - cost).quantize(Decimal('0.01'))

    @property
    def marketer_commission_amount(self):
        """Calculates the linked marketer's commission percentage based on net store revenue."""
        if hasattr(self.customer, 'referred_by') and self.customer.referred_by:
            commission_pct = getattr(self.customer.referred_by, 'commission_percentage', Decimal('5.00'))
            return (self.net_store_revenue * (Decimal(str(commission_pct)) / Decimal('100.00'))).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @property
    def is_fully_settled(self):
        """Returns True if the order has been fully paid or closed/completed."""
        return self.status in ['full_payment_confirmed', 'balance_paid', 'delivered', 'completed']

    @property
    def escrow_liability_amount(self):
        """Isolates partial payment escrow liabilities from recognized settled revenue."""
        if self.payment_type == 'partial' and not self.balance_paid and not self.is_fully_settled:
            return self.balance_amount
        return Decimal('0.00')

    @property
    def recognized_settled_revenue(self):
        """Calculates actual realized revenue excluding outstanding escrow balances."""
        if self.is_fully_settled or self.balance_paid:
            return self.total_amount
        elif self.payment_type == 'partial':
            return self.deposit_amount
        return Decimal('0.00')

    # --- Progress Bar Helper Properties ---
    @property
    def progress_bar_class(self):
        if self.status == 'delivered':
            return 'bg-success'
        elif self.status in ['picked_up', 'arrived_at_customer']:
            return 'bg-primary'
        elif self.status == 'order_ready':
            return 'bg-info'
        return 'bg-warning'

    @property
    def progress_width(self):
        if self.status == 'delivered':
            return '100%'
        elif self.status in ['picked_up', 'arrived_at_customer']:
            return '75%'
        elif self.status == 'order_ready':
            return '50%'
        return '25%'


class StoreReturnPolicy(models.Model):
    """
    Stores the official store return and refund policy managed exclusively 
    by the CEO or General Manager, displayed on the customer refund request page.
    """
    title = models.CharField(max_length=200, default="Official Store Return & Refund Policy")
    content = models.TextField(help_text="Detailed terms and conditions for returns and refunds.")
    policy_document = models.FileField(upload_to='policies/', blank=True, null=True, help_text="Optional downloadable PDF document.")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title


class StoreReturnRequest(models.Model):
    """
    Handles the rigorous 3-day return/refund process including multimedia proofs,
    rider tracking logistics, management verification, and finance settlement.
    """
    STATUS_CHOICES = (
        ('pending_management_approval', 'Pending Management Approval'),
        ('rider_assigned', 'Rider Assigned for Pickup'),
        ('going_to_site', 'Rider Going to Site for Pickup'),
        ('picked_up', 'Rider Picked Up Goods'),
        ('delivered_to_store', 'Delivered to Store (Pending Inspection)'),
        ('approved_pending_finance', 'Approved by Management (Pending Finance Refund)'),
        ('refunded_and_closed', 'Refund Executed by Finance (Closed)'),
        ('rejected_and_closed', 'Rejected by Management (Closed)'),
    )

    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name='return_requests')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_returns')
    
    # Form details
    reason = models.ForeignKey(RefundReason, on_delete=models.SET_NULL, null=True, help_text="Reason selected from CEO dropdown list")
    issue_description = models.TextField(help_text="Detailed explanation of the issue with the goods")
    
    # Mandatory media (At least 3 images and 1 video required in validation forms)
    image_1 = models.ImageField(upload_to='store/returns/images/')
    image_2 = models.ImageField(upload_to='store/returns/images/')
    image_3 = models.ImageField(upload_to='store/returns/images/')
    video_proof = models.FileField(upload_to='store/returns/videos/', help_text="Required video showing proof of issue")
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending_management_approval')
    
    # Logistics Tracking
    assigned_rider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='rider_return_pickups'
    )
    rider_status = models.CharField(
        max_length=30,
        choices=(
            ('none', 'Not Assigned'),
            ('going_to_site', 'Going to site for pickup'),
            ('picked_up', 'Picked up'),
            ('delivered_to_store', 'Delivered to store')
        ),
        default='none'
    )
    
    # Inspection & Decision by CEO, GM, or Manager
    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='inspected_returns'
    )
    inspection_notes = models.TextField(blank=True, null=True, help_text="Notes from management physical store inspection")
    
    # Rejection Fields (if management rejects)
    rejection_reason_note = models.TextField(blank=True, null=True, help_text="Reason why refund was rejected")
    rejection_proof_file = models.FileField(upload_to='store/returns/rejections/', blank=True, null=True, help_text="Optional PDF or image proof for rejection")
    
    # Finance Settlement Fields
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Exact amount refunded by finance")
    refund_invoice = models.FileField(upload_to='store/returns/invoices/', blank=True, null=True, help_text="Refund invoice PDF or image uploaded by finance")
    refund_processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='processed_refunds'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return Request #{self.id} for Order #{self.order.id} - {self.get_status_display()}"


class StoreReturnItem(models.Model):
    """Tracks specific order items selected for return, their individual quantities, and unit/total prices."""
    return_request = models.ForeignKey(StoreReturnRequest, on_delete=models.CASCADE, related_name='returned_items')
    order_item = models.ForeignKey('StoreOrderItem', on_delete=models.CASCADE)
    quantity_to_return = models.PositiveIntegerField(default=1)
    refund_item_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.quantity_to_return} x {self.order_item.product.name} (Return #{self.return_request.id})"


class DeliveryMovementLog(models.Model):
    """Stores movement history checkpoints exclusively for CEO, General Manager, and Manager review."""
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name='movement_logs')
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log for Order #{self.order.id} at ({self.latitude}, {self.longitude}) on {self.recorded_at}"


class StoreOrderItem(models.Model):
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Store the snapshot of the vendor price at the time of purchase
    vendor_unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        # Automatically inherit the product's current vendor price if not explicitly set
        if not self.vendor_unit_price and self.product:
            self.vendor_unit_price = self.product.vendor_price
        super().save(*args, **kwargs)
        # Update parent order's total vendor cost aggregation
        self.order.update_vendor_cost()

    def delete(self, *args, **kwargs):
        order_ref = self.order
        super().delete(*args, **kwargs)
        order_ref.update_vendor_cost()

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order.id})"


class StoreInvoice(models.Model):
    INVOICE_TYPE_CHOICES = (
        ('partial', 'Partial Payment Invoice'),
        ('full', 'Full Payment Invoice (100%)'),
        ('balance', 'Balance Settlement Invoice'),
    )
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES, default='full')
    amount_billed = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    invoice_pdf = models.FileField(upload_to='store/invoices/', blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice #{self.invoice_number} ({self.get_invoice_type_display()})"


class StoreRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings', blank=True, null=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store_ratings')
    rating_score = models.PositiveIntegerField(default=5)  # 1 to 5 stars
    comment = models.TextField(blank=True, null=True)
    is_ceo_adjusted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.product.name if self.product else "General Store"
        return f"Rating {self.rating_score}/5 by {self.customer.username} for {target}"


class Wishlist(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'product')

    def __str__(self):
        return f"{self.customer.username}'s Wishlist: {self.product.name}"


class BrowsingHistory(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='browsing_history')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.username} viewed {self.product.name}"


class ActivityAuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    action = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp}] {self.user} ({self.role}): {self.action}"


class CompanyPolicy(models.Model):
    TITLE_CHOICES = (
        ('return_policy', 'Return & Replacement Policy'),
        ('delivery_policy', 'Delivery Policy'),
        ('terms_conditions', 'Terms & Conditions'),
        ('about_us', 'About Us'),
    )
    policy_type = models.CharField(max_length=50, choices=TITLE_CHOICES, unique=True)
    content_text = models.TextField(blank=True, null=True)
    policy_pdf = models.FileField(upload_to='store/policies/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_policy_type_display()


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store_notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}"


class CompanyBankAccount(models.Model):
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, help_text="Only one active account should be shown to customers.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Input account details for store"
        verbose_name_plural = "Input account details for store"

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"


class TaxRateProposal(models.Model):
    """
    Allows Finance to propose a new VAT/tax percentage, 
    which remains inactive until explicitly approved by the CEO or General Manager.
    """
    proposed_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, 
        help_text="Requested tax rate percentage (e.g. 7.50 or 10.00)"
    )
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='tax_proposals'
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending CEO / General Manager Approval'),
            ('approved', 'Approved & Active'),
            ('rejected', 'Rejected')
        ),
        default='pending'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_tax_changes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tax Proposal: {self.proposed_percentage}% ({self.get_status_display()})"
