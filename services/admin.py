from django.contrib import admin
from .models import (
    User, Job, Quotation, Invoice, SiteConfiguration, JobType, 
    InstructionCatalog, CompanyInfo, CompanyBankAccount,
    SupportTicket, TicketMessage, TicketRating
)

# Customize TechsNi Admin branding headers
admin.site.site_header = "TechsNi Administration"
admin.site.site_title = "TechsNi Admin Portal"
admin.site.index_title = "Welcome to TechsNi Management Portal"

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_email', 'google_email_id')
    fieldsets = (
        ('Company Contact Details', {
            'fields': ('company_name', 'contact_phone', 'contact_email')
        }),
        ('Google / Gmail API & SMTP Settings', {
            'fields': ('google_email_id', 'google_app_password'),
            'description': 'Enter your registered Google console credentials / App password to send emails dynamically.'
        }),
        ('About Us Information', {
            'fields': ('about_text', 'about_pdf')
        }),
        ('Company Policy', {
            'fields': ('policy_text', 'policy_pdf')
        }),
    )

    def has_add_permission(self, request):
        # Prevent creating multiple config rows (Singleton)
        return not SiteConfiguration.objects.exists()


# --- INSTRUCTION CATALOG ADMIN CONFIGURATION ---
@admin.register(InstructionCatalog)
class InstructionCatalogAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')
    list_editable = ('order',)
    search_fields = ('title', 'description')
    fieldsets = (
        ('Catalog Information', {
            'fields': ('title', 'description', 'order')
        }),
        ('Media & Documents', {
            'fields': ('image', 'pdf_document'),
            'description': 'Upload a unique display image and instructions PDF for this catalog category.'
        }),
    )


@admin.register(JobType)
class JobTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'employee_id', 'first_name', 'last_name', 'email', 'role', 'phone_number', 'is_verified')
    list_filter = ('role', 'is_verified', 'state')
    search_fields = ('username', 'employee_id', 'email', 'phone_number', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'employee_id', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Location Info', {'fields': ('country', 'state', 'capital', 'lga', 'address')}),
        ('Role & Custom Details', {'fields': ('role', 'description', 'narration', 'commission_percentage', 'referred_by')}),
        ('Verification & Status', {'fields': ('is_verified', 'otp_code', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permissions & Groups', {'fields': ('groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_type', 'model_type', 'customer', 'assigned_worker', 'status', 'created_at')
    list_filter = ('job_type', 'status', 'created_at')
    search_fields = ('job_type__name', 'model_type', 'serial_number', 'customer__username', 'customer__first_name', 'customer__last_name', 'assigned_worker__username')

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('job', 'total_amount', 'deposit_amount', 'balance_amount', 'is_approved_by_client', 'is_deposit_paid')
    list_filter = ('is_approved_by_client', 'is_deposit_paid', 'is_balance_paid', 'created_at')
    search_fields = ('job__id', 'job__model_type', 'job__customer__username')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'job', 'generated_at')
    list_filter = ('generated_at',)
    search_fields = ('invoice_number', 'job__id', 'job__customer__username')

@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ('__str__',)

@admin.register(CompanyBankAccount)
class CompanyBankAccountAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_number', 'account_name', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    search_fields = ('bank_name', 'account_number', 'account_name')


# --- UNIFIED CUSTOMER SERVICE HELPDESK ADMIN REGISTRATIONS ---
@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'assigned_agent', 'app_source', 'subject', 'status', 'created_at')
    list_filter = ('status', 'app_source', 'created_at')
    search_fields = ('subject', 'customer__username', 'assigned_agent__username')

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'sender_type', 'timestamp')
    list_filter = ('sender_type', 'timestamp')

@admin.register(TicketRating)
class TicketRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'customer', 'agent', 'score', 'created_at')
    list_filter = ('score', 'created_at')