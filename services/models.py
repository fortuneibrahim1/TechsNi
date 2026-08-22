from decimal import Decimal
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings


class User(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    ROLE_CHOICES = (
        ('ceo', 'CEO'),
        ('general_manager', 'General Manager'),
        ('manager', 'Manager'),
        ('assistant_manager', 'Assistant Manager'),
        ('customer_service', 'Customer Service Representative'),
        ('worker', 'Worker'),
        ('customer', 'Customer'),
        ('marketer', 'Marketer'),
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='customer')
    
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="ID Number")
    email = models.EmailField(unique=True, blank=False, null=False)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    country = models.CharField(max_length=50, default='Nigeria')
    state = models.CharField(max_length=100, blank=True, null=True)
    capital = models.CharField(max_length=100, blank=True, null=True)
    lga = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    description = models.TextField(blank=True, null=True)
    narration = models.TextField(blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)

    # Individual custom commission percentage for marketers (optional)
    commission_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True, 
        verbose_name="Custom Commission Percentage (%)"
    )

    # Marketer Referral Relation Field
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')

    def __str__(self):
        id_str = f" [ID: {self.employee_id}]" if self.employee_id else ""
        name_str = f" - {self.first_name} {self.last_name}" if (self.first_name or self.last_name) else ""
        return f'{self.username}{id_str}{name_str} ({self.get_role_display()})'


class SiteConfiguration(models.Model):
    """Singleton model to store dynamic admin portal contact, banking, and policies."""
    company_name = models.CharField(max_length=150, default="TechsNi Services")
    company_address = models.TextField(blank=True, null=True, verbose_name="Company Office Address")
    contact_phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Company Call Number")
    contact_email = models.EmailField(blank=True, null=True, verbose_name="Official Contact Email")
    
    # Default global commission rate
    commission_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00, 
        verbose_name="Default Global Commission Percentage (%)"
    )

    # Financial Account Configuration fields for Quotation/Invoice display
    bank_name = models.CharField(max_length=100, blank=True, null=True, default="Wema Bank / First Bank")
    account_number = models.CharField(max_length=50, blank=True, null=True, default="0123456789")
    account_name = models.CharField(max_length=150, blank=True, null=True, default="TechsNi Global Services")

    google_email_id = models.EmailField(blank=True, null=True, verbose_name="Google Gmail Address")
    google_app_password = models.CharField(max_length=100, blank=True, null=True, verbose_name="Google App Password / Secret Code")

    about_text = models.TextField(blank=True, null=True, verbose_name="About Us Text")
    about_pdf = models.FileField(upload_to='site/about/', blank=True, null=True, verbose_name="About Us PDF Document")

    policy_text = models.TextField(blank=True, null=True, verbose_name="Company Policy Text")
    policy_pdf = models.FileField(upload_to='site/policies/', blank=True, null=True, verbose_name="Company Policy PDF Document")

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SiteConfiguration, self).save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Global Site & Financial Configuration"


# --- DYNAMIC INSTRUCTION CATALOG MODEL (Managed by CEO) ---
class InstructionCatalog(models.Model):
    title = models.CharField(max_length=150, verbose_name="Catalog Title (e.g., How to Register)")
    description = models.TextField(verbose_name="Detailed Instruction Write-up")
    image = models.ImageField(upload_to='instructions/images/', blank=True, null=True, verbose_name="Catalog Display Image")
    pdf_document = models.FileField(upload_to='instructions/pdfs/', blank=True, null=True, verbose_name="Instruction Unique PDF")
    order = models.PositiveIntegerField(default=0, verbose_name="Display Order")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class JobType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Job Service Type")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    def __str__(self):
        return self.name


class Job(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('quote_sent', 'Quote Sent'),
        ('quote_approved', 'Quote Approved'),
        ('quote_rejected', 'Quote Rejected'),
        ('deposit_paid', 'Deposit Paid'),
        ('on_site', 'Worker On-Site'),
        ('in_progress', 'Work in Progress'),
        ('completed', 'Work Completed'),
        ('fully_paid', 'Fully Paid & Invoiced'),
        ('pending_finance_review', 'Pending Finance Review'),
        ('settled', 'Settled & Closed'),
    )

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_requests')
    job_type = models.ForeignKey(JobType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Job Type")
    model_type = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    condition = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    
    image1 = models.ImageField(upload_to='jobs/images/', blank=True, null=True)
    image2 = models.ImageField(upload_to='jobs/images/', blank=True, null=True)
    image3 = models.ImageField(upload_to='jobs/images/', blank=True, null=True)
    
    video = models.FileField(upload_to='jobs/videos/', blank=True, null=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    assigned_worker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs')
    
    is_po_job = models.BooleanField(default=False)
    po_number = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        j_type = self.job_type.name if self.job_type else "Job"
        return f'{j_type} #{self.id} ({self.customer.username})'


# --- NEW: JOB EXPENSE & OVERHEAD TRACKING MODEL ---
class JobExpense(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='expense_record')
    logged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='logged_job_expenses')
    
    amount_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Amount Spent on Overhead / Parts (₦)")
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Remaining Balance (₦)")
    
    transfer_invoice = models.FileField(upload_to='expenses/invoices/', blank=True, null=True, verbose_name="Transfer Invoice / Receipt (PDF or Image)")
    invoice_number_or_note = models.CharField(max_length=150, blank=True, null=True, verbose_name="Invoice Number or Reference Note")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Expenses for Job #{self.job.id} - Spent: ₦{self.amount_spent}"
        
        
class Quotation(models.Model):
    title = models.CharField(max_length=255)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Discount (₦)")
    deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Deposit Percentage (%)")
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="VAT / Tax (₦)")
    quotation_pdf = models.FileField(upload_to='quotations/pdfs/', blank=True, null=True, verbose_name="Upload Quotation PDF")
    
    # Missing fields expected by QuotationAdmin
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Balance Amount (₦)")
    is_approved_by_client = models.BooleanField(default=False, verbose_name="Approved by Client")
    is_deposit_paid = models.BooleanField(default=False, verbose_name="Deposit Paid")
    is_balance_paid = models.BooleanField(default=False, verbose_name="Balance Paid")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title


class QuotationItem(models.Model):
    quotation = models.ForeignKey('Quotation', on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255, verbose_name="Item / Service Description")
    serial_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Unit Amount (₦)")
    
    confidential_vendor_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, 
        verbose_name="Confidential Vendor Price (₦)"
    )

    def get_total(self):
        return (self.quantity or 1) * (self.amount or Decimal('0.00'))

    def get_vendor_total(self):
        return (self.quantity or 1) * (self.confidential_vendor_price or Decimal('0.00'))

    def __str__(self):
        return f"{self.description} (Qty: {self.quantity}) - ₦{self.get_total()}"


class PurchaseOrderRecord(models.Model):
    APPROVAL_STATUS_CHOICES = (
        ('pending_finance_review', 'Pending Finance Review'),
        ('pending_executive_approval', 'Pending CEO / GM Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('payment_pending_confirmation', 'Payment Pending Confirmation'),
        ('settled', 'Settled'),
    )

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='purchase_order')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchase_orders')
    
    po_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Customer PO Number")
    po_document = models.FileField(upload_to='purchase_orders/pdfs/', verbose_name="Attached PO Document (PDF/Image)")
    payment_terms = models.CharField(max_length=100, default="Net 30 Days", verbose_name="Payment Terms")
    due_date = models.DateField(null=True, blank=True, verbose_name="Calculated PO Due Date")
    
    status = models.CharField(max_length=50, choices=APPROVAL_STATUS_CHOICES, default='pending_finance_review')
    finance_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_approved_pos')
    executive_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='executive_approved_pos')
    
    reminder_7day_sent = models.BooleanField(default=False, verbose_name="7-Day Reminder Sent")
    reminder_2day_sent = models.BooleanField(default=False, verbose_name="2-Day Reminder Sent")
    
    customer_marked_paid = models.BooleanField(default=False, verbose_name="Customer Marked as Paid")
    finance_confirmed_payment = models.BooleanField(default=False, verbose_name="Finance Confirmed Settlement")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PO for Job #{self.job.id} - Status: {self.status}"


class StatementOfAccount(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='statements_of_account')
    invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='statements')
    statement_pdf = models.FileField(upload_to='statements/pdfs/', verbose_name="Statement of Account PDF")
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_statements')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Statement of Account for Job #{self.job.id} (Invoice: {self.invoice.invoice_number if self.invoice else 'N/A'})"


class Invoice(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Discount (₦)")
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="VAT / Tax (₦)")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    invoice_pdf = models.FileField(upload_to='invoices/pdfs/', blank=True, null=True, verbose_name="Upload Invoice PDF")
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Invoice {self.invoice_number}'


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255, verbose_name="Item / Service Description")
    serial_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Unit Amount (₦)")

    def get_total(self):
        return (self.quantity or 1) * (self.amount or Decimal('0.00'))

    def __str__(self):
        return f"{self.description} (Qty: {self.quantity}) - ₦{self.get_total()}"


class ServiceJobArchive(models.Model):
    job_id = models.IntegerField()
    client_name = models.CharField(max_length=150)
    assigned_staff = models.CharField(max_length=150, blank=True, null=True)
    job_description = models.TextField()
    job_flow_status = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    has_quotation = models.BooleanField(default=False)
    job_day = models.CharField(max_length=20)
    job_month = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Archive Job #{self.job_id} - {self.client_name} ({self.job_month})"


class CompanyInfo(models.Model):
    about_us_text = models.TextField(default="Welcome to TechsNi Portal...")
    company_policy_pdf = models.FileField(upload_to='policies/', blank=True, null=True, help_text="Upload CEO / Admin Company Policy PDF")

    def __str__(self):
        return "Company Info & Policies (Managed by CEO)"


class MarketerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='marketer_profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Marketer: {self.user.username}"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() < self.created_at + timedelta(minutes=10)


class CompanyBankAccount(models.Model):
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, help_text="Only one active account should be shown on invoices and quotations.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Service Bank Account"
        verbose_name_plural = "Service Bank Accounts"

    def save(self, *args, **kwargs):
        if self.is_active:
            CompanyBankAccount.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number} ({'Active' if self.is_active else 'Inactive'})"


class SupportTicket(models.Model):
    APP_SOURCE_CHOICES = (
        ('service', 'Service Portal'),
        ('store', 'Store App'),
    )
    STATUS_CHOICES = (
        ('bot_active', 'Handling by AI Bot'),
        ('pending_agent', 'Waiting for CSR'),
        ('in_progress', 'Claimed / In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets', limit_choices_to={'role': 'customer_service'})
    app_source = models.CharField(max_length=20, choices=APP_SOURCE_CHOICES, default='service', verbose_name="App Origin")
    subject = models.CharField(max_length=200, verbose_name="Inquiry Subject")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='bot_active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject} ({self.get_status_display()})"


class TicketMessage(models.Model):
    SENDER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('bot', 'AI Bot'),
        ('agent', 'Customer Service Rep'),
    )

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_ticket_messages')
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPE_CHOICES)
    message = models.TextField(verbose_name="Message Content")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.sender_type}] on Ticket #{self.ticket.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class TicketRating(models.Model):
    ticket = models.OneToOneField(SupportTicket, on_delete=models.CASCADE, related_name='rating')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_ratings')
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_ratings', limit_choices_to={'role': 'customer_service'})
    score = models.PositiveIntegerField(default=5, verbose_name="Rating Score (1-5)")
    feedback = models.TextField(blank=True, null=True, verbose_name="Customer Feedback Note")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        score_stars = '★' * self.score + '☆' * (5 - self.score)
        agent_name = self.agent.username if self.agent else "Unassigned"
        return f"Rating: {score_stars} for Agent {agent_name} (Ticket #{self.ticket.id})"
