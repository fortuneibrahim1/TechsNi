from django.contrib import admin
from django.contrib.auth import get_user_model

# Fetch the active user model safely if needed internally
User = get_user_model()

# Import store models safely
from .models import (
    Category, Product, StoreOrder, StoreOrderItem, 
    StoreInvoice,StoreRating, Wishlist, CompanyPolicy, 
    CompanyBankAccount, Notification, PromoTheme, StoreGlobalSetting,
    ActivityAuditLog
)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock_quantity', 'allow_partial_payment', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'allow_partial_payment', 'created_at')
    search_fields = ('name', 'description', 'internal_brand_tag', 'visual_search_tag')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('price', 'stock_quantity', 'is_active')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'description', 'price', 'discount_price', 'promo_theme', 'promo_price', 'stock_quantity', 'image', 'visual_search_tag')
        }),
        ('Confidential & Financial Controls', {
            'fields': ('internal_brand_tag', 'allow_partial_payment', 'partial_deposit_percentage', 'is_active'),
            'classes': ('collapse',)
        }),
    )

class StoreOrderItemInline(admin.TabularInline):
    model = StoreOrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price', 'total_price')

from django.contrib import admin
from .models import Vendor

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(StoreOrder)
class StoreOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'customer__username', 'customer__email')
    inlines = [StoreOrderItemInline]

@admin.register(StoreGlobalSetting)
class StoreGlobalSettingAdmin(admin.ModelAdmin):
    list_display = ('partial_payment_threshold', 'default_deposit_percentage', 'shipping_fee_below_threshold', 'updated_at')
    
    def has_add_permission(self, request):
        # Enforce singleton model (only 1 global settings record allowed)
        return not StoreGlobalSetting.objects.exists()

@admin.register(CompanyBankAccount)
class CompanyBankAccountAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_number', 'account_name', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('bank_name', 'account_number', 'account_name')

@admin.register(ActivityAuditLog)
class ActivityAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'role', 'action')
    list_filter = ('role', 'timestamp')
    search_fields = ('user__username', 'action')
    readonly_fields = ('timestamp', 'user', 'role', 'action')

# Register your other store models safely
admin.site.register(Category)
admin.site.register(PromoTheme)
admin.site.register(StoreOrderItem)
admin.site.register(StoreInvoice)
admin.site.register(StoreRating)
admin.site.register(Wishlist)
admin.site.register(CompanyPolicy)
admin.site.register(Notification)