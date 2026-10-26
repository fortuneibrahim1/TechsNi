import socket
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import StoreOrder, StoreReturnRequest, Notification

User = get_user_model()

# Allowed staff roles for notifications
ALLOWED_STAFF_ROLES = ['ceo', 'general_manager', 'finance', 'manager', 'customer_service']

def get_staff_emails(roles=None):
    """Utility function to fetch emails for designated staff roles."""
    target_roles = roles if roles else ALLOWED_STAFF_ROLES
    return list(
        User.objects.filter(role__in=target_roles, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )

def send_clean_mail(subject, plain_message, recipient_list):
    """Sends clean email with lightweight inline HTML to prevent spam triggers and timeouts."""
    if not recipient_list:
        return
    
    # Safe multiline replacement handled outside template/f-string to prevent Python 3.11 syntax errors
    formatted_message = plain_message.replace('\n', '<br>')
    
    # Simple inline HTML wrapper that inbox providers trust
    html_message = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #222222; padding: 10px;">
        <p>{formatted_message}</p>
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin-top: 20px;">
        <p style="font-size: 12px; color: #777777;">TechsNi Store | support@techsni.com.ng</p>
      </body>
    </html>
    """
    
    try:
        # Enforce 5-second socket timeout so checkout never freezes
        socket.setdefaulttimeout(5)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=True
        )
    except Exception:
        pass

# Pre-save signal to track original order status
@receiver(pre_save, sender=StoreOrder)
def track_order_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_status = StoreOrder.objects.get(pk=instance.pk).status
        except StoreOrder.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

# Store Order Created or Status Changed
@receiver(post_save, sender=StoreOrder)
def notify_order_status_change(sender, instance, created, **kwargs):
    staff_emails = get_staff_emails()
    
    # 1. New Order Placed
    if created:
        Notification.objects.create(
            user=instance.customer,
            message=f"Order #{instance.id} has been placed successfully."
        )
        
        # Email Customer
        if instance.customer.email:
            total_amt = f"₦{instance.total_amount:,.2f}"
            status_disp = instance.get_status_display()
            subject = f"Store Order Confirmation #{instance.id}"
            message = f"Hello {instance.customer.username},\n\nThank you for your order! Your order total is {total_amt}.\nStatus: {status_disp}"
            send_clean_mail(subject, message, [instance.customer.email])
            
        # Email Management & Finance
        if staff_emails:
            total_amt = f"₦{instance.total_amount:,.2f}"
            payment_disp = instance.get_payment_type_display()
            subject = f"NEW STORE ORDER #{instance.id}"
            message = f"New order placed by {instance.customer.username}.\nTotal Amount: {total_amt}\nPayment Type: {payment_disp}"
            send_clean_mail(subject, message, staff_emails)

    # 2. Status Changed
    elif hasattr(instance, '_previous_status') and instance._previous_status != instance.status:
        status_disp = instance.get_status_display()
        Notification.objects.create(
            user=instance.customer,
            message=f"Order #{instance.id} updated to {status_disp}."
        )
        
        recipients = list(staff_emails)
        if instance.customer.email:
            recipients.append(instance.customer.email)
            
        if hasattr(instance, 'assigned_rider') and instance.assigned_rider and instance.assigned_rider.email:
            recipients.append(instance.assigned_rider.email)
            
        if recipients:
            subject = f"Order #{instance.id} Status: {status_disp}"
            message = f"Store Order #{instance.id} for {instance.customer.username} has updated to: {status_disp}."
            send_clean_mail(subject, message, list(set(recipients)))

# Return / Refund Request Signals
@receiver(post_save, sender=StoreReturnRequest)
def notify_return_request_status(sender, instance, created, **kwargs):
    staff_emails = get_staff_emails(['ceo', 'general_manager', 'finance', 'manager', 'customer_service'])
    status_disp = instance.get_status_display()
    
    if created:
        recipients = list(set(staff_emails + ([instance.customer.email] if instance.customer.email else [])))
        subject = f"RETURN REQUEST: Order #{instance.order.id}"
        message = f"A return request has been submitted by {instance.customer.username} for Order #{instance.order.id}.\nReason: {instance.issue_description}"
        send_clean_mail(subject, message, recipients)
    else:
        recipients = list(staff_emails)
        if instance.customer.email:
            recipients.append(instance.customer.email)
        if hasattr(instance, 'assigned_rider') and instance.assigned_rider and instance.assigned_rider.email:
            recipients.append(instance.assigned_rider.email)

        subject = f"Return Request #{instance.id} Status: {status_disp}"
        message = f"Return Request #{instance.id} (Order #{instance.order.id}) updated to: {status_disp}."
        send_clean_mail(subject, message, list(set(recipients)))