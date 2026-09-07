from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import StoreOrder, StoreReturnRequest, Notification

User = get_user_model()

# Allowed staff roles for notifications
ALLOWED_STAFF_ROLES = ['ceo', 'general_manager', 'finance', 'manager']

def get_staff_emails(roles=None):
    """Utility function to fetch emails for designated staff roles."""
    target_roles = roles if roles else ALLOWED_STAFF_ROLES
    return list(
        User.objects.filter(role__in=target_roles, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )

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
            send_mail(
                subject=f"Store Order Confirmation #{instance.id}",
                message=f"Hello {instance.customer.username},\n\nYour order total is ₦{instance.total_amount}.\nStatus: {instance.get_status_display()}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.customer.email],
                fail_silently=True
            )
            
        # Email Management & Finance
        if staff_emails:
            send_mail(
                subject=f"NEW STORE ORDER #{instance.id}",
                message=f"New order placed by {instance.customer.username}.\nTotal Amount: ₦{instance.total_amount}\nPayment Type: {instance.get_payment_type_display()}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=staff_emails,
                fail_silently=True
            )

    # 2. Status Changed
    elif hasattr(instance, '_previous_status') and instance._previous_status != instance.status:
        Notification.objects.create(
            user=instance.customer,
            message=f"Order #{instance.id} updated to {instance.get_status_display()}."
        )
        
        recipients = list(staff_emails)
        if instance.customer.email:
            recipients.append(instance.customer.email)
            
        # Include assigned Rider
        if instance.assigned_rider and instance.assigned_rider.email:
            recipients.append(instance.assigned_rider.email)
            
        if recipients:
            send_mail(
                subject=f"Order #{instance.id} Status: {instance.get_status_display()}",
                message=f"Store Order #{instance.id} for {instance.customer.username} has updated to: {instance.get_status_display()}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=list(set(recipients)),
                fail_silently=True
            )

# Return / Refund Request Signals
@receiver(post_save, sender=StoreReturnRequest)
def notify_return_request_status(sender, instance, created, **kwargs):
    staff_emails = get_staff_emails(['ceo', 'general_manager', 'finance', 'manager'])
    
    if created:
        recipients = list(set(staff_emails + ([instance.customer.email] if instance.customer.email else [])))
        send_mail(
            subject=f"RETURN REQUEST: Order #{instance.order.id}",
            message=f"A return request has been submitted by {instance.customer.username} for Order #{instance.order.id}.\nReason: {instance.issue_description}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=True
        )
    else:
        recipients = list(staff_emails)
        if instance.customer.email:
            recipients.append(instance.customer.email)
        if instance.assigned_rider and instance.assigned_rider.email:
            recipients.append(instance.assigned_rider.email)

        send_mail(
            subject=f"Return Request #{instance.id} Status: {instance.get_status_display()}",
            message=f"Return Request #{instance.id} (Order #{instance.order.id}) updated to: {instance.get_status_display()}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(set(recipients)),
            fail_silently=True
        )