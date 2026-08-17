from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .views import login_view
from services.views import public_pdf_view

urlpatterns = [
    path('', login_view, name='home_login'),
    path('dashboard-router/', views.dashboard_router, name='dashboard_router'),
    path('login/', login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # --- CUSTOM OTP PASSWORD RESET ROUTES ---
    path('password-reset/', views.custom_password_reset_request, name='password_reset'),
    path('password-reset/verify/', views.verify_otp_view, name='verify_otp'),
    path('password-reset/new/', views.set_new_password_view, name='set_new_password'),

    # --- REGISTRATION & SIGNUP OTP ROUTES ---
    path('register/', views.register_view, name='register'),
    path('register/verify/', views.verify_signup_otp_view, name='signup_verify_otp'),

    # --- ABOUT US & COMPANY POLICY ROUTES ---
    path('about/', views.about_us_view, name='about_us'),
    path('company-policy/', views.company_policy_view, name='company_policy'),

    path('api/check-username/', views.check_username, name='check_username'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/customer/submit/', views.submit_job_view, name='submit_job'),
    path('dashboard/customer/quote/', views.respond_quote_view, name='respond_quote'),
    path('dashboard/customer/pay/', views.pay_balance_view, name='pay_balance'),
    path('dashboard/ceo/', views.ceo_dashboard, name='ceo_dashboard'),
    path('dashboard/manager/', views.manager_dashboard, name='manager_dashboard'),
    path('dashboard/worker/', views.worker_dashboard, name='worker_dashboard'),
    
    # --- GENERAL MANAGER EXPENSE & OVERHEAD ROUTE ---
    path('dashboard/general-manager/job/<int:job_id>/expense/', views.general_manager_job_expense_view, name='general_manager_job_expense_view'),
    
    # --- CUSTOMER SERVICE (CSR) DASHBOARD & HELPDESK ROUTES ---
    path('dashboard/csr/', views.csr_dashboard, name='csr_dashboard'),
    path('dashboard/csr/ticket/<int:ticket_id>/', views.csr_ticket_detail_view, name='csr_ticket_detail'),
    path('dashboard/csr/ticket/<int:ticket_id>/claim/', views.csr_claim_ticket, name='csr_claim_ticket'),
    path('support/chat/', views.customer_support_chat_view, name='customer_support_chat'),
    path('support/ticket/<int:ticket_id>/rate/', views.rate_support_ticket, name='rate_support_ticket'),
    path('support/transcribe/', views.transcribe_voice_note, name='transcribe_voice_note'),
    
    # Finance Dashboard Routes
    path('dashboard/finance/', views.finance_dashboard, name='finance_dashboard'),
    path('dashboard/finance/quotations/', views.finance_quotations_view, name='finance_quotations'),
    path('dashboard/finance/part-payments/', views.finance_part_payments_view, name='finance_part_payments'),
    path('dashboard/finance/invoices/', views.finance_invoices_view, name='finance_invoices'),

    # PDF Download Routes
    path('invoice/<int:job_id>/pdf/', views.download_invoice_pdf, name='download_invoice_pdf'),
    path('quotation/<int:job_id>/pdf/', views.download_quotation_pdf, name='download_quotation_pdf'),

    path('ceo/impersonate/<int:user_id>/', views.ceo_impersonate_user, name='ceo_impersonate_user'),

    path('dashboard/ceo/jobs/', views.ceo_jobs_view, name='ceo_jobs'),
    path('dashboard/ceo/users/', views.ceo_users_view, name='ceo_users'),
    path('dashboard/manager/jobs/', views.manager_jobs_view, name='manager_jobs'),
    
    # CEO Admin Shortcut Route
    path('ceo/admin-shortcut/', views.ceo_admin_shortcut_view, name='ceo_admin_shortcut'),

    path('dashboard/assign-worker/', views.assign_worker_ajax_view, name='assign_worker'),

    # --- DEDICATED VIEWS ---
    path('customer/job/<int:job_id>/', views.customer_job_detail_view, name='customer_job_detail'),
    path('dashboard/customer/jobs/', views.customer_jobs_list_view, name='customer_jobs_list'),

    path('dashboard/worker/update-status/', views.update_worker_job_status, name='update_worker_job_status'),

    # --- ARCHIVE & EXPORT ROUTES ---
    path('dashboard/archives/jobs/', views.service_job_history_view, name='service_job_history'),
    path('dashboard/archives/export/csv/', views.export_service_history_excel, name='export_service_history_excel'),
    path('dashboard/archives/export/pdf/', views.export_service_history_pdf, name='export_service_history_pdf'),
    
    path('ceo/user/<int:user_id>/update-role/', views.ceo_update_user_role, name='ceo_update_user_role'),
    path('ceo/user/<int:user_id>/update-commission/', views.ceo_update_user_commission, name='ceo_update_user_commission'),

    path('dashboard/marketer-analytics/', views.marketer_analytics_view, name='marketer_analytics'),
    path('dashboard/marketer/', views.marketer_dashboard_view, name='marketer_dashboard'),
    path('dashboard/ceo/edit-config/', views.edit_site_config_view, name='edit_site_config'),

    path('dashboard/catalogs/', views.manage_catalogs_view, name='manage_catalogs'),
    path('dashboard/catalogs/add/', views.add_catalog_view, name='add_catalog'),
    path('dashboard/catalogs/edit/<int:pk>/', views.edit_catalog_view, name='edit_catalog'),
    path('dashboard/catalogs/delete/<int:pk>/', views.delete_catalog_view, name='delete_catalog'),
    path('instructions/', views.instruction_catalog_view, name='instruction_catalogs'), 

    path('ceo/bank-accounts/', views.service_bank_accounts_view, name='service_bank_accounts'),
    path('finance/confirm-balance/<int:quotation_id>/', views.confirm_balance_paid, name='confirm_balance_paid'),

    path('finance/completed-invoices/', views.finance_invoices_view, name='finance_invoice'),
    path('ceo/settings/', views.ceo_site_settings_view, name='ceo_site_settings'),
    path('ceo/settings/', views.ceo_site_settings_view, name='company_contact_settings'),

    # --- PURCHASE ORDER (PO) & STATEMENT WORKFLOW ROUTES ---
    path('dashboard/customer/po/submit/<int:job_id>/', views.customer_submit_po_view, name='customer_submit_po'),
    path('dashboard/finance/po/review/', views.finance_po_list_view, name='finance_po_list'),
    path('dashboard/finance/po/approve/<int:po_id>/', views.finance_approve_po_view, name='finance_approve_po'),
    path('dashboard/executive/po/approve/<int:po_id>/', views.executive_approve_po_view, name='executive_approve_po'),
    path('dashboard/finance/statement/upload/<int:job_id>/', views.finance_upload_statement_view, name='finance_upload_statement'),
    path('dashboard/customer/po/pay-confirm/<int:po_id>/', views.customer_confirm_po_payment_view, name='customer_confirm_po_payment'),
    path('dashboard/finance/po/confirm-settlement/<int:po_id>/', views.finance_confirm_po_settlement_view, name='finance_confirm_po_settlement'),

    path('customer/job/<int:job_id>/approve-po/', views.customer_approve_via_po, name='customer_approve_via_po'),
    path('services/customer/job/<int:job_id>/pay-notification/', views.customer_po_payment_notification, name='customer_po_payment_notification'),

    path('services/job/<int:job_id>/view-pdf/', public_pdf_view, name='public_pdf_view'),

]