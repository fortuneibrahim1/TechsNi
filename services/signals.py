from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Job, Quotation, PurchaseOrderRecord, SupportTicket, TicketMessage

User = get_user_model()

# Designated management, admin, and customer support staff roles
ALLOWED_STAFF_ROLES = ['ceo', 'general_manager', 'finance', 'manager', 'customer_service']

def get_staff_emails(roles=None):
    """Utility function to fetch emails for designated staff roles."""
    target_roles = roles if roles else ALLOWED_STAFF_ROLES
    return list(
        User.objects.filter(role__in=target_roles, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )

# Pre-save signal to track original job status
@receiver(pre_save, sender=Job)
def track_job_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_status = Job.objects.get(pk=instance.pk).status
        except Job.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

# Job Created or Status Changed
@receiver(post_save, sender=Job)
def notify_job_status_change(sender, instance, created, **kwargs):
    staff_emails = get_staff_emails()
    
    # 1. New Job Created
    if created:
        if instance.customer.email:
            send_mail(
                subject=f"Service Job #{instance.id} Received",
                message=f"Hello {instance.customer.username},\n\nYour service job request has been received and is currently under review.\n\nThank you for choosing TechsNi.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.customer.email],
                fail_silently=True
            )
        
        if staff_emails:
            send_mail(
                subject=f"NEW JOB SUBMITTED: Job #{instance.id}",
                message=f"A new service job request (#{instance.id}) has been submitted by customer {instance.customer.username}.\n\nDescription: {instance.description}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=staff_emails,
                fail_silently=True
            )

    # 2. Job Status Updated
    elif hasattr(instance, '_previous_status') and instance._previous_status != instance.status:
        recipients = list(staff_emails)
        if instance.customer.email:
            recipients.append(instance.customer.email)
            
        # Include assigned worker/technician if allocated
        if hasattr(instance, 'assigned_worker') and instance.assigned_worker and instance.assigned_worker.email:
            recipients.append(instance.assigned_worker.email)

        if recipients:
            send_mail(
                subject=f"Job #{instance.id} Status Updated: {instance.get_status_display()}",
                message=f"Job #{instance.id} ({instance.customer.username}) status updated to: {instance.get_status_display()}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=list(set(recipients)),
                fail_silently=True
            )

# Quotation Issued Notification
@receiver(post_save, sender=Quotation)
def notify_quotation_issued(sender, instance, created, **kwargs):
    if created and instance.job:
        recipients = get_staff_emails(['ceo', 'general_manager', 'finance', 'manager'])
        if instance.job.customer.email:
            recipients.append(instance.job.customer.email)
            
        if recipients:
            send_mail(
                subject=f"Quotation Issued for Job #{instance.job.id}",
                message=f"A quotation of ₦{instance.total_amount} has been issued for Job #{instance.job.id}.\n\nDeposit Required: ₦{instance.deposit_amount}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=list(set(recipients)),
                fail_silently=True
            )

# Purchase Order Notification
@receiver(post_save, sender=PurchaseOrderRecord)
def notify_purchase_order_status(sender, instance, created, **kwargs):
    po_reviewers = get_staff_emails(['ceo', 'general_manager', 'finance', 'manager'])
    
    if created:
        recipients = list(set(po_reviewers + ([instance.customer.email] if instance.customer.email else [])))
        send_mail(
            subject=f"PO Uploaded for Job #{instance.job.id}",
            message=f"Purchase Order ({instance.po_number or 'N/A'}) was uploaded by {instance.customer.username} and is pending review.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=True
        )

# Support Ticket Message Alert (Customer Chat Alerts)
@receiver(post_save, sender=TicketMessage)
def notify_support_message(sender, instance, created, **kwargs):
    if created:
        # Customer sends a message or complaint -> Notify Customer Service & Managers
        if instance.sender_type == 'customer':
            cs_emails = get_staff_emails(['customer_service', 'manager', 'ceo', 'general_manager'])
            if cs_emails:
                send_mail(
                    subject=f"New Customer Message on Ticket #{instance.ticket.id}",
                    message=f"Customer {instance.ticket.customer.username} sent a message/complaint:\n\n\"{instance.message}\"\n\nPlease log in to respond.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=cs_emails,
                    fail_silently=True
                )
        # Agent or Bot sends a reply -> Notify Customer
        elif instance.sender_type in ['agent', 'bot']:
            if instance.ticket.customer.email:
                send_mail(
                    subject=f"Support Response - Ticket #{instance.ticket.id}",
                    message=f"Hello {instance.ticket.customer.username},\n\nYou received a response:\n\n\"{instance.message}\"",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.ticket.customer.email],
                    fail_silently=True
                )