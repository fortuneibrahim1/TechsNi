import threading
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
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

def _send_email_thread(msg):
    """Executes message sending inside a background thread."""
    try:
        msg.send(fail_silently=True)
    except Exception:
        pass

def send_html_email(subject, text_message, html_message, recipient_list):
    """Helper to construct multi-part HTML emails sent asynchronously in a background thread."""
    if not recipient_list:
        return
    
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
        reply_to=['support@techsni.com.ng']
    )
    msg.attach_alternative(html_message, "text/html")
    
    # Run email sending asynchronously so checkout HTTP response returns immediately
    threading.Thread(target=_send_email_thread, args=(msg,)).start()

def generate_order_items_html(instance):
    """Dynamically builds HTML table rows for ordered items including product images."""
    items_html = ""
    # Attempt to pull items if related name exists (e.g., items or orderitem_set)
    items = getattr(instance, 'items', None) or getattr(instance, 'orderitem_set', None)
    if items:
        for item in items.all():
            product_name = getattr(item.product, 'name', 'Product')
            quantity = getattr(item, 'quantity', 1)
            price = getattr(item, 'price', 0)
            
            # Fetch product image URL
            image_url = "https://techsni.com.ng/static/store/logo.jpg"
            if hasattr(item.product, 'image') and item.product.image:
                try:
                    image_url = item.product.image.url
                except Exception:
                    pass

            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">
                    <img src="{image_url}" alt="{product_name}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px;">
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; color: #333; font-weight: bold;">
                    {product_name}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center; color: #555;">
                    x{quantity}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; color: #111; font-weight: bold;">
                    ₦{price:,.2f}
                </td>
            </tr>
            """
    return items_html

def wrap_email_template(title, content_body):
    """Wraps core email content in branded HTML layout with TechsNi logo."""
    logo_url = "https://techsni.com.ng/static/store/logo.jpg"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            .header {{ background-color: #ffffff; padding: 20px; text-align: center; border-bottom: 2px solid #f0f0f0; }}
            .header img {{ max-width: 160px; height: auto; display: block; margin: 0 auto; }}
            .content {{ padding: 30px; color: #333333; line-height: 1.6; }}
            .order-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px; }}
            .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #777777; border-top: 1px solid #eeeeee; }}
            .status-badge {{ display: inline-block; background-color: #e7f1ff; color: #0d6efd; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{logo_url}" alt="TechsNi Logo">
            </div>
            <div class="content">
                <h2 style="color: #111; margin-top: 0;">{title}</h2>
                {content_body}
            </div>
            <div class="footer">
                <p>&copy; TechsNi Store. All rights reserved.</p>
                <p>Need help? Contact us at <a href="mailto:support@techsni.com.ng" style="color: #0d6efd; text-decoration: none;">support@techsni.com.ng</a></p>
            </div>
        </div>
    </body>
    </html>
    """

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
        
        items_html = generate_order_items_html(instance)
        items_section = f"""
        <table class="order-table">
            <thead>
                <tr style="background-color: #f8f9fa;">
                    <th style="padding: 10px; border-bottom: 2px solid #ddd;">Item</th>
                    <th style="padding: 10px; border-bottom: 2px solid #ddd; text-align: left;">Name</th>
                    <th style="padding: 10px; border-bottom: 2px solid #ddd;">Qty</th>
                    <th style="padding: 10px; border-bottom: 2px solid #ddd; text-align: right;">Price</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        """ if items_html else ""

        # Email Customer
        if instance.customer.email:
            subject = f"Store Order Confirmation #{instance.id}"
            text_msg = f"Hello {instance.customer.username},\n\nYour order total is ₦{instance.total_amount}.\nStatus: {instance.get_status_display()}"
            
            html_body = f"""
            <p>Hello <strong>{instance.customer.username}</strong>,</p>
            <p>Thank you for your order! We have received your order <strong>#{instance.id}</strong> and are currently preparing it.</p>
            {items_section}
            <p style="font-size: 16px;"><strong>Total Amount:</strong> <span style="color: #0d6efd;">₦{instance.total_amount:,.2f}</span></p>
            <p><strong>Status:</strong> <span class="status-badge">{instance.get_status_display()}</span></p>
            """
            
            send_html_email(subject, text_msg, wrap_email_template(f"Order #{instance.id} Confirmed", html_body), [instance.customer.email])
            
        # Email Management & Finance
        if staff_emails:
            subject = f"NEW STORE ORDER #{instance.id}"
            text_msg = f"New order placed by {instance.customer.username}.\nTotal Amount: ₦{instance.total_amount}\nPayment Type: {instance.get_payment_type_display()}"
            
            html_body = f"""
            <p>A new order has been placed on TechsNi Store.</p>
            <p><strong>Customer:</strong> {instance.customer.username} ({instance.customer.email})</p>
            <p><strong>Payment Method:</strong> {instance.get_payment_type_display()}</p>
            {items_section}
            <p style="font-size: 16px;"><strong>Total Amount:</strong> ₦{instance.total_amount:,.2f}</p>
            """
            
            send_html_email(subject, text_msg, wrap_email_template(f"New Order #{instance.id} Received", html_body), staff_emails)

    # 2. Status Changed
    elif hasattr(instance, '_previous_status') and instance._previous_status != instance.status:
        Notification.objects.create(
            user=instance.customer,
            message=f"Order #{instance.id} updated to {instance.get_status_display()}."
        )
        
        recipients = list(staff_emails)
        if instance.customer.email:
            recipients.append(instance.customer.email)
            
        if hasattr(instance, 'assigned_rider') and instance.assigned_rider and instance.assigned_rider.email:
            recipients.append(instance.assigned_rider.email)
            
        if recipients:
            unique_recipients = list(set(recipients))
            subject = f"Order #{instance.id} Status: {instance.get_status_display()}"
            text_msg = f"Store Order #{instance.id} for {instance.customer.username} has updated to: {instance.get_status_display()}."
            
            html_body = f"""
            <p>Hello,</p>
            <p>The status for Store Order <strong>#{instance.id}</strong> has been updated.</p>
            <p><strong>Customer:</strong> {instance.customer.username}</p>
            <p><strong>New Status:</strong> <span class="status-badge">{instance.get_status_display()}</span></p>
            """
            
            send_html_email(subject, text_msg, wrap_email_template(f"Order #{instance.id} Update", html_body), unique_recipients)

# Return / Refund Request Signals
@receiver(post_save, sender=StoreReturnRequest)
def notify_return_request_status(sender, instance, created, **kwargs):
    staff_emails = get_staff_emails(['ceo', 'general_manager', 'finance', 'manager', 'customer_service'])
    
    if created:
        recipients = list(set(staff_emails + ([instance.customer.email] if instance.customer.email else [])))
        subject = f"RETURN REQUEST: Order #{instance.order.id}"
        text_msg = f"A return request has been submitted by {instance.customer.username} for Order #{instance.order.id}.\nReason: {instance.issue_description}"
        
        html_body = f"""
        <p>A new return/refund request has been submitted.</p>
        <p><strong>Order ID:</strong> #{instance.order.id}</p>
        <p><strong>Customer:</strong> {instance.customer.username}</p>
        <p><strong>Reason / Issue:</strong></p>
        <blockquote style="background: #f8f9fa; padding: 10px; border-left: 4px solid #0d6efd; margin: 0;">
            {instance.issue_description}
        </blockquote>
        """
        
        send_html_email(subject, text_msg, wrap_email_template(f"Return Request for Order #{instance.order.id}", html_body), recipients)
    else:
        recipients = list(staff_emails)
        if instance.customer.email:
            recipients.append(instance.customer.email)
        if hasattr(instance, 'assigned_rider') and instance.assigned_rider and instance.assigned_rider.email:
            recipients.append(instance.assigned_rider.email)

        unique_recipients = list(set(recipients))
        subject = f"Return Request #{instance.id} Status: {instance.get_status_display()}"
        text_msg = f"Return Request #{instance.id} (Order #{instance.order.id}) updated to: {instance.get_status_display()}."
        
        html_body = f"""
        <p>The status of Return Request <strong>#{instance.id}</strong> (Order #{instance.order.id}) has changed.</p>
        <p><strong>Current Status:</strong> <span class="status-badge">{instance.get_status_display()}</span></p>
        """
        
        send_html_email(subject, text_msg, wrap_email_template(f"Return Request #{instance.id} Updated", html_body), unique_recipients)