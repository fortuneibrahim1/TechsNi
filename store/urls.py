from django.urls import path
from . import views

urlpatterns = [
    # Storefront & Browsing
    path('', views.store_home_view, name='store_home'),
    path('product/<str:product_slug>/', views.product_detail_view, name='store_product_detail'),
    path('product/wishlist/toggle/<int:product_id>/', views.toggle_wishlist_view, name='toggle_wishlist'),
    
    # Customer Hubs & Cart
    path('cart/', views.cart_view, name='store_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart_view, name='store_add_to_cart'),
    path('cart/remove/<str:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout_view, name='store_checkout'),
    path('order/invoice/<int:order_id>/', views.customer_invoices_view, name='order_invoice'),
    path('orders/', views.customer_orders_list_view, name='customer_orders_list'),
    path('order/<int:order_id>/', views.store_order_detail_view, name='store_order_detail'),
    path('my-invoices/', views.customer_invoices_view, name='customer_invoices'),
    path('my-wishlist/', views.customer_wishlist_view, name='customer_wishlist'),
    path('my-browsing-history/', views.customer_browsing_history_view, name='customer_browsing_history'),
    

    # Staff & Admin Dashboards (Including General Manager & CEO Controls)
    path('dashboard/keeper/', views.store_keeper_dashboard, name='store_keeper_dashboard'),
    path('dashboard/finance/', views.store_finance_dashboard, name='store_finance_dashboard'),
    path('dashboard/manager/', views.store_manager_dashboard, name='store_manager_dashboard'),
    path('dashboard/ceo/', views.store_ceo_dashboard, name='store_ceo_dashboard'),
    path('dashboard/rider/', views.store_rider_dashboard, name='store_rider_dashboard'),
    path('dashboard/dispatch-logs/', views.ceo_gm_dispatch_logs_view, name='dispatch_logs_view'),

    # --- Return & Refund Management, Rider & Finance Workflows ---
    path('services/management/returns/', views.management_return_dashboard_view, name='management_return_dashboard'),
    path('services/rider/return/<int:return_id>/update-status/', views.rider_return_status_update_view, name='rider_return_status_update'),
    path('services/finance/return/<int:return_id>/settle/', views.finance_refund_settlement_view, name='finance_refund_settlement'),

    # Export Utilities
    path('export/audit-logs/', views.export_audit_logs_csv, name='export_audit_logs'),
    path('export/ceo-transactions/', views.export_ceo_transactions_csv, name='export_ceo_transactions_csv'),
    path('export/ceo-inventory/', views.export_ceo_inventory_csv, name='export_ceo_inventory_csv'),
    path('services/returns/export-csv/', views.export_refunds_csv_view, name='export_refunds_csv'),

    # User Profile, Notifications & Account Management
    path('profile/', views.user_profile_view, name='user_profile'),
    path('profile/delete/', views.delete_account_view, name='delete_account'),
    path('gateway/', views.portal_gateway_view, name='gateway'),
    path('ceo/impersonate/<int:user_id>/', views.impersonate_user, name='impersonate_user'),
    path('notifications/', views.notification_list_view, name='notification_list'),
    path('notifications/clear/', views.clear_notifications_view, name='clear_notifications'),

    # Company Policies
    path('policies/', views.company_policy_view, name='company_policies'),
    path('policies/<slug:policy_slug>/', views.company_policy_view, name='company_policy_detail'),

    # APIs & Fallback Aliases
    path('api/sync-marketer/', views.api_sync_marketer, name='api_sync_marketer'),

    # Preserved Template Aliases
    path('cart/add-alias/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('wishlist/toggle-alias/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    path('dashboard/general-manager/', views.general_manager_dashboard, name='general_manager_dashboard'),

    path('dashboard/price-discounts/', views.price_discount_approvals_view, name='price_discount_approvals'),

    path('cart/update/<int:product_id>/', views.update_cart_quantity_view, name='update_cart_quantity'),

    path('product/<int:product_id>/rate/', views.submit_product_rating_view, name='submit_product_rating'),
    # --- Return & Refund Customer Workflow ---
    
    path('store/order/<int:order_id>/refund/request/', views.request_store_refund_view, name='request_refund'),


    path('store/ceo/return-policy/', views.ceo_manage_return_policy, name='ceo_manage_return_policy'),

    # Rider Dashboard URL
    path('rider/dashboard/', views.store_rider_dashboard, name='store_rider_dashboard'),
    
    # Rider Return Status Update URL (matches the form action in your rider template)
    path('rider/return/<int:return_id>/update/', views.rider_return_status_update_view, name='rider_return_status_update'),
]