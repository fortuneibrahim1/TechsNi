import csv
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.mail import send_mail
import random
from decimal import Decimal
from django.template.loader import render_to_string
from .forms import CustomUserRegistrationForm, JobRequestForm, QuotationForm
from .models import Invoice, Job, Quotation, User, SiteConfiguration, ServiceJobArchive, InstructionCatalog
from django.contrib import messages
from .forms import CustomUserRegistrationForm, JobRequestForm, QuotationForm
from django.contrib.auth import authenticate, login


from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from services.models import InstructionCatalog # Adjust your app name if needed
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from .models import InstructionCatalog
from .models import Invoice, Job, Quotation, User, SiteConfiguration, ServiceJobArchive, InstructionCatalog, CompanyBankAccount
from django.contrib.auth.forms import AuthenticationForm
from services.models import InstructionCatalog

import qrcode
import base64
from io import BytesIO
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from .models import InstructionCatalog  # Assuming this is where your catalog model is
from django.shortcuts import redirect, render


import base64
from io import BytesIO
import qrcode
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from .models import InstructionCatalog


def login_view(request):
  catalogs = InstructionCatalog.objects.all().order_by("order")

  # Robust QR Code Generation
  qr_base64 = None
  try:
    portal_url = request.build_absolute_uri()
    # Fallback to a safe base string if URI is empty
    if not portal_url:
      portal_url = "http://127.0.0.1:8000/"

    qr = qrcode.QRCode(
        version=None,  # Auto-fit version
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(portal_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
  except Exception as e:
    print("--- QR GENERATION EXCEPTION:", e)
    portal_url = "http://127.0.0.1:8000/"
    # Ultimate fallback static generation to prevent blank views
    try:
      img = qrcode.make(portal_url)
      buffer = BytesIO()
      img.save(buffer, format="PNG")
      qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    except Exception as inner_e:
      print("--- CRITICAL QR ERROR:", inner_e)
      qr_base64 = None

  if request.method == "POST":
    form = AuthenticationForm(request, data=request.POST)
    if form.is_valid():
      user = form.get_user()
      login(request, user)
      return redirect("dashboard_router")
  else:
    form = AuthenticationForm()

  context = {
      "form": form,
      "catalogs": catalogs,
      "portal_url": portal_url,
      "qr_code_image": qr_base64,
  }
  return render(request, "services/login.html", context)

@login_required
def dashboard_router(request):
    request.user.refresh_from_db()
    user = request.user
    role = str(user.role).strip().lower() if user.role else 'customer'
   
    if user.is_superuser or role == 'ceo':
        return redirect('ceo_dashboard')
    elif role in ['manager', 'general_manager', 'assistant_manager']:
        return redirect('manager_dashboard')
    elif role == 'finance':
        return redirect('finance_dashboard')
    elif role == 'worker':
        return redirect('worker_dashboard')
    elif role == 'marketer':
        return redirect('marketer_dashboard')
    elif role == 'customer_service':
        return redirect('csr_dashboard')  # <-- Added Customer Service Dashboard redirect
    else:
        return redirect('customer_dashboard')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Avg
from .models import SupportTicket, TicketMessage, TicketRating, Job, User

# --- CSR DASHBOARD VIEW ---
@login_required
def csr_dashboard(request):
    user = request.user
    # Ensure only CSR, Manager, GM, or CEO can access
    allowed_roles = ['customer_service', 'ceo', 'general_manager', 'manager', 'assistant_manager']
    if user.role not in allowed_roles and not user.is_superuser:
        return redirect('dashboard_router')

    # Unassigned tickets waiting for a CSR to claim
    pending_tickets = SupportTicket.objects.filter(status__in=['pending_agent', 'bot_active'], assigned_agent__isnull=True).order_by('-created_at')
    
    # Active tickets assigned to the logged-in CSR
    my_tickets = SupportTicket.objects.filter(assigned_agent=user).exclude(status__in=['resolved', 'closed']).order_by('-updated_at')
    
    # Recently resolved tickets
    resolved_tickets = SupportTicket.objects.filter(status__in=['resolved', 'closed']).order_by('-updated_at')[:20]

    # CSR Performance Rating Metrics
    ratings = TicketRating.objects.filter(agent=user) if user.role == 'customer_service' else TicketRating.objects.all()
    avg_rating = ratings.aggregate(Avg('score'))['score__avg'] or 0.0

    context = {
        'pending_tickets': pending_tickets,
        'my_tickets': my_tickets,
        'resolved_tickets': resolved_tickets,
        'ratings': ratings[:10],
        'avg_rating': round(avg_rating, 1),
    }
    return render(request, 'services/dashboards/csr_dashboard.html', context)


# --- CLAIM TICKET ACTION ---
@login_required
def csr_claim_ticket(request, ticket_id):
    if request.user.role not in ['customer_service', 'ceo', 'general_manager', 'manager'] and not request.user.is_superuser:
        return HttpResponseForbidden("Unauthorized")

    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    if not ticket.assigned_agent:
        ticket.assigned_agent = request.user
        ticket.status = 'in_progress'
        ticket.save()
        
        # System notification inside chat
        TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            sender_type='agent',
            message=f"Agent {request.user.get_full_name() or request.user.username} has joined the conversation and claimed this ticket."
        )

    return redirect('csr_ticket_detail', ticket_id=ticket.id)


# --- TICKET DETAIL / CHAT VIEW FOR STAFF & MANAGEMENT ---
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from openai import OpenAI
client = OpenAI(api_key="your-actual-openai-api-key-here")

@login_required
def csr_ticket_detail_view(request, ticket_id):
    user = request.user
    allowed_roles = [
        'customer_service',
        'ceo',
        'general_manager',
        'manager',
        'assistant_manager',
    ]
    if user.role not in allowed_roles and not user.is_superuser:
        return redirect('dashboard_router')

    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    messages = ticket.messages.all().order_by('timestamp')

    if request.method == 'POST':
        action = request.POST.get('action')

        # --- MICROPHONE / AUDIO TRANSCRIPTION HANDLER ---
        if action == 'transcribe_audio' or request.FILES.get('audio'):
            try:
                audio_file = request.FILES.get('audio')
                if audio_file:
                    filename = getattr(audio_file, 'name', 'audio.webm')
                    content_type = getattr(audio_file, 'content_type', 'audio/webm')
                    file_tuple = (filename, audio_file.read(), content_type)

                    transcript = client.audio.transcriptions.create(
                        model='whisper-1', file=file_tuple
                    )
                    transcript_text = (
                        transcript.text
                        if hasattr(transcript, 'text')
                        else str(transcript)
                    )

                    return JsonResponse(
                        {'status': 'success', 'transcript': transcript_text}
                    )
                else:
                    return JsonResponse(
                        {'status': 'error', 'message': 'No audio file found.'},
                        status=400,
                    )
            except Exception as e:
                print('--- TRANSCRIPTION ERROR:', e)
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

        elif action == 'send_message':
            msg_text = request.POST.get('message', '').strip()
            if msg_text:
                TicketMessage.objects.create(
                    ticket=ticket,
                    sender=user,
                    sender_type='agent',
                    message=msg_text,
                )
                if ticket.status == 'pending_agent':
                    ticket.status = 'in_progress'
                    ticket.save()

        elif action == 'resolve_ticket':
            ticket.status = 'resolved'
            ticket.save()
            TicketMessage.objects.create(
                ticket=ticket,
                sender=user,
                sender_type='agent',
                message=(
                    'This support request has been marked as RESOLVED. Thank you for'
                    ' reaching out!'
                ),
            )

        return redirect('csr_ticket_detail', ticket_id=ticket.id)

    context = {
        'ticket': ticket,
        'messages': messages,
    }
    return render(request, 'services/dashboards/csr_ticket_detail.html', context)


# --- CUSTOMER SUPPORT CHAT & AUTOMATED BOT LOGIC (UNIFIED WITH STORE APP) ---
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from store.models import StoreOrder

@login_required
def customer_po_payment_notification(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    po_record = PurchaseOrderRecord.objects.filter(job=job).first()
    
    if po_record:
        po_record.status = 'payment_pending_confirmation' # or whatever your pending status field is
        po_record.save()
        messages.success(request, "Payment notification sent to finance successfully!")
    
    return redirect('customer_job_detail', job_id=job.id)

@login_required
def customer_support_chat_view(request):
    user = request.user
    active_ticket = SupportTicket.objects.filter(customer=user).exclude(status__in=['resolved', 'closed']).first()

    if request.method == 'POST':
        user_msg = request.POST.get('message', '').strip()
        request_agent = request.POST.get('request_agent', False)

        if not active_ticket:
            active_ticket = SupportTicket.objects.create(
                customer=user,
                subject="General Inquiry / Support Request",
                app_source='service',
                status='bot_active'
            )

        if user_msg:
            TicketMessage.objects.create(
                ticket=active_ticket,
                sender=user,
                sender_type='customer',
                message=user_msg
            )

            if active_ticket.status == 'bot_active':
                msg_lower = user_msg.lower()
                bot_reply = None

                # Branch 1: Service Problem Selected
                if 'service problem' in msg_lower or 'service' in msg_lower:
                    job_types = JobType.objects.filter(is_active=True).values_list('name', flat=True)
                    services_str = ", ".join(job_types) if job_types else "General Repairs, Tracking, and Quotes"
                    bot_reply = f"🤖 AI Assistant: For our **Service app**, I can help you with: {services_str}. Would you like to check your active job status or speak with an agent?"

                # Branch 2: Store Problem Selected (Now pulling live store order stats!)
                elif 'store problem' in msg_lower or 'store' in msg_lower or 'order' in msg_lower:
                    latest_order = StoreOrder.objects.filter(customer=user).order_by('-created_at').first()
                    if latest_order:
                        bot_reply = f"🤖 AI Assistant: For our **Store app**, your recent order #{latest_order.id} status is '{latest_order.get_status_display()}' (Total: ₦{latest_order.total_amount}). Need help with inventory or payment confirmation?"
                    else:
                        bot_reply = "🤖 AI Assistant: For our **Store app**, I can assist you with product inventory, order inquiries, and checkout. You have no recent store orders found."

                # Branch 3: Job Status Query
                elif 'status' in msg_lower or 'repair' in msg_lower or 'job' in msg_lower:
                    latest_job = Job.objects.filter(customer=user).order_by('-created_at').first()
                    if latest_job:
                        bot_reply = f"🤖 AI Assistant: Your latest job #{latest_job.id} ({latest_job.job_type.name if latest_job.job_type else 'Service'}) is currently set to: '{latest_job.get_status_display()}'."
                    else:
                        bot_reply = "🤖 AI Assistant: You currently have no active service/repair orders on file."
                
                # Branch 4: Live Agent Escalation
                elif 'agent' in msg_lower or 'human' in msg_lower or 'representative' in msg_lower or request_agent:
                    active_ticket.status = 'pending_agent'
                    active_ticket.save()
                    bot_reply = "🤖 AI Assistant: Connecting you to an available Customer Service Representative. Please wait..."
                
                # Default Fallback / Guidance
                else:
                    bot_reply = "🤖 AI Assistant: I can help you with store issues, service orders, job statuses, or connect you to a live support representative. Type 'Agent' anytime to speak with a human."

                if bot_reply:
                    TicketMessage.objects.create(
                        ticket=active_ticket,
                        sender_type='bot',
                        message=bot_reply
                    )

        return redirect('customer_support_chat')

    messages = active_ticket.messages.all().order_by('timestamp') if active_ticket else []
    
    context = {
        'active_ticket': active_ticket,
        'messages': messages,
    }
    return render(request, 'services/dashboards/customer_support_chat.html', context)


# --- NEW: VOICE NOTE TRANSCRIPTION ENDPOINT ---
import os
import openai
from django.conf import settings


from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from openai import OpenAI

# Initialize OpenAI client with your API key
client = OpenAI(api_key="sk-proj-YOUR_ACTUAL_KEY_HERE")

@csrf_exempt
@login_required
def transcribe_voice_note(request):
  if request.method == 'POST':
    try:
      # Check multiple possible key names sent from frontend JS
      audio_file = (
          request.FILES.get('audio')
          or request.FILES.get('audio_file')
          or request.FILES.get('file')
          or request.FILES.get('voice')
      )

      if audio_file:
        filename = getattr(audio_file, 'name', 'audio.webm')
        content_type = getattr(audio_file, 'content_type', 'audio/webm')
        file_tuple = (filename, audio_file.read(), content_type)

        # Call OpenAI Whisper API safely using the file tuple
        transcript = client.audio.transcriptions.create(
            model='whisper-1', file=file_tuple
        )
        transcript_text = (
            transcript.text if hasattr(transcript, 'text') else str(transcript)
        )

        return JsonResponse({'status': 'success', 'transcript': transcript_text})
      else:
        print('--- FAILED FILES KEYS RECEIVED:', list(request.FILES.keys()))
        print('--- POST DATA RECEIVED:', list(request.POST.keys()))
        return JsonResponse(
            {
                'status': 'error',
                'message': (
                    'No audio file provided under any expected key.'
                ),
            },
            status=400,
        )
    except Exception as e:
      import traceback

      traceback.print_exc()
      return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

  return JsonResponse(
      {'status': 'error', 'message': 'Invalid request method.'}, status=405
  )

# --- CUSTOMER RATING SUBMISSION ---
@login_required
def rate_support_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id, customer=request.user)
    if request.method == 'POST':
        score = int(request.POST.get('score', 5))
        feedback = request.POST.get('feedback', '').strip()
        
        TicketRating.objects.update_or_create(
            ticket=ticket,
            defaults={
                'customer': request.user,
                'agent': ticket.assigned_agent,
                'score': score,
                'feedback': feedback
            }
        )
        ticket.status = 'closed'
        ticket.save()
        return redirect('customer_dashboard')

    return render(request, 'services/dashboards/rate_ticket.html', {'ticket': ticket})

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import Quotation, PurchaseOrderRecord

@login_required
def respond_quote_view(request):
    """
    Handles customer response to quotation, standard approvals, 
    and dedicated manual corporate PO submissions.
    """
    if request.method == 'POST':
        quote_id = request.POST.get('quote_id')
        action = request.POST.get('action')
        quote = get_object_or_404(Quotation, id=quote_id, job__customer=request.user)
       
        if action == 'approve':
            quote.is_approved_by_client = True
            quote.save()
            quote.job.status = 'quote_approved'
            quote.job.save()

        elif action == 'submit_manual_po':
            # --- DEDICATED MANUAL CORPORATE PO PROCESSING ---
            po_number = request.POST.get('po_number')
            payment_terms = request.POST.get('payment_terms', 'Net 30 Days')
            due_date_str = request.POST.get('due_date')
            po_document = request.FILES.get('po_document')
            
            # Parse the manually provided due date string into a date object
            parsed_due_date = None
            if due_date_str:
                try:
                    parsed_due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Save details onto the Job instance
            quote.job.is_po_job = True
            if po_number:
                quote.job.po_number = po_number
            if po_document:
                quote.job.purchase_order = po_document
            quote.job.save()
            
            # Create or update the PurchaseOrderRecord tracking entry with the manual inputs
            po_record, created = PurchaseOrderRecord.objects.get_or_create(
                job=quote.job,
                defaults={
                    'customer': request.user,
                    'po_number': po_number if po_number else f"PO-JOB-{quote.job.id}",
                    'payment_terms': payment_terms,
                    'due_date': parsed_due_date,
                    'po_document': po_document,
                    'status': 'pending_finance_review'
                }
            )
            
            po_record.customer = request.user
            if po_number:
                po_record.po_number = po_number
            if payment_terms:
                po_record.payment_terms = payment_terms
            if parsed_due_date:
                po_record.due_date = parsed_due_date
            if po_document:
                po_record.po_document = po_document
                
            po_record.status = 'pending_finance_review'
            po_record.save()
            
            # Mark quote and job status as pending finance review
            quote.is_approved_by_client = True
            quote.save()
            quote.job.status = 'pending_finance_review'
            quote.job.save()
            # -----------------------------------------------

        elif action == 'reject':
            reason = request.POST.get('rejection_reason', 'No reason provided')
            quote.rejection_reason = reason
            quote.save()
            quote.job.status = 'quote_rejected'
            quote.job.save()
            
        elif action == 'i_have_paid':
            quote.is_deposit_paid = True 
            quote.save()
            quote.job.status = 'payment_submitted'
            quote.job.save()
           
        return redirect('customer_job_detail', job_id=quote.job.id)
        
    return redirect('customer_dashboard')

@login_required
def pay_balance_view(request):
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        job = get_object_or_404(Job, id=job_id, customer=request.user)
        if hasattr(job, 'quotation'):
            quote = job.quotation
            # Keep balance paid as False until Finance confirms it!
            # Set pending status so finance knows to review it.
            job.status = 'balance_payment_submitted'
            job.save()
             
    # Redirect cleanly back to the specific job details page instead of the general dashboard
    return redirect('customer_job_detail', job_id=job.id)

@login_required
def ceo_dashboard(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
       
    if request.method == 'POST':
        if 'approve_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'approved'
            job.save()
            return redirect('ceo_dashboard')
        elif 'reject_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'rejected'
            job.save()
            return redirect('ceo_dashboard')

    status_filter = request.GET.get('status', '')
    all_jobs = Job.objects.all().order_by('-id')
    if status_filter:
        all_jobs = all_jobs.filter(status=status_filter)

    live_jobs = Job.objects.all().order_by('-id')
    users = User.objects.all().order_by('-id')
    workers = User.objects.filter(role='worker')

    return render(request, 'services/dashboards/ceo.html', {
        'live_jobs': live_jobs,
        'all_jobs': all_jobs,
        'users': users,
        'workers': workers,
        'selected_status': status_filter
    })

from .forms import SiteConfigurationForm # Ensure this is imported at the top of your views.py

@login_required
def ceo_site_settings_view(request):
    """Allows the CEO to update company details such as contact email, phone number, and configurations."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
        
    # SiteConfiguration usually uses a singleton pattern (getting or creating the first instance)
    config, created = SiteConfiguration.objects.get_or_create(id=1)

    if request.method == 'POST':
        form = SiteConfigurationForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Company site settings updated successfully! Email and phone changes will automatically reflect on invoices and quotations.")
            return redirect('ceo_site_settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SiteConfigurationForm(instance=config)

    return render(request, 'services/dashboards/ceo_site_settings.html', {
        'form': form,
        'config': config
    })

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import User

@login_required
def ceo_update_user_role(request, user_id):
    """Allows the CEO to instantly change user roles from the frontend UI and sync marketers to the store."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
        
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        valid_roles = ['ceo', 'manager', 'general_manager', 'assistant_manager', 'finance', 'customer_service', 'worker', 'customer', 'marketer']
        
        if new_role in valid_roles:
            target_user.role = new_role
            target_user.save()
            messages.success(request, f"Updated {target_user.username}'s role to {new_role}.")
            
            # --- API SYNC FOR MARKETERS ONLY ---
            if new_role == 'marketer':
                store_api_url = 'https://your-store-app-url.com/api/sync-marketer/' # Replace with your actual store URL endpoint
                payload = {
                    'email': target_user.email,
                    'username': target_user.username,
                    'first_name': target_user.first_name,
                    'last_name': target_user.last_name,
                    'role': 'marketer'
                }
                try:
                    response = requests.post(store_api_url, data=payload, timeout=5)
                    if response.status_code == 200:
                        messages.success(request, f"Successfully synced {target_user.username} as a marketer to the Store app.")
                except requests.exceptions.RequestException:
                    messages.warning(request, "Role updated locally, but failed to sync to store app automatically.")

    return redirect(request.META.get('HTTP_REFERER', 'ceo_users'))


@login_required
def ceo_update_user_commission(request, user_id):
    """Allows the CEO or Manager to set an individual custom commission rate for a marketer."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager']:
        return redirect('dashboard_router')
        
    target_user = get_object_or_404(User, id=user_id, role='marketer')
    
    if request.method == 'POST':
        commission_input = request.POST.get('commission_percentage', '').strip()
        
        if commission_input == '':
            target_user.commission_percentage = None
            messages.success(request, f"Cleared custom commission for {target_user.username}. Now using global default.")
        else:
            try:
                rate = float(commission_input)
                if 0 <= rate <= 100:
                    target_user.commission_percentage = rate
                    messages.success(request, f"Successfully updated custom commission for {target_user.username} to {rate}%!")
                else:
                    messages.error(request, "Commission percentage must be between 0 and 100.")
            except ValueError:
                messages.error(request, "Invalid commission percentage format.")
                
        target_user.save()

    return redirect(request.META.get('HTTP_REFERER', 'ceo_users'))

@login_required
def ceo_admin_shortcut_view(request):
    request.user.refresh_from_db()
    if request.user.is_superuser or request.user.role == 'ceo':
        if not request.user.is_staff:
            request.user.is_staff = True
            request.user.save()
        return redirect('/admin/')
    return redirect('dashboard_router')


@login_required
def manager_dashboard(request):
    request.user.refresh_from_db()
    role = str(request.user.role).strip().lower() if request.user.role else ''
    if not request.user.is_superuser and role not in ['manager', 'general_manager', 'assistant_manager', 'ceo']:
        return redirect('dashboard_router')
   
    if request.method == 'POST':
        if 'approve_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'approved'
            job.save()
            return redirect('manager_dashboard')
        elif 'reject_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'rejected'
            job.save()
            return redirect('manager_dashboard')
        elif 'assign_job' in request.POST:
            job_id = request.POST.get('job_id')
            worker_id = request.POST.get('worker_id')
            job = get_object_or_404(Job, id=job_id)
            worker = get_object_or_404(User, id=worker_id, role='worker')
            job.assigned_worker = worker
            job.status = 'on_site'
            job.save()
            return redirect('manager_dashboard')

    status_filter = request.GET.get('status', '')
    all_jobs = Job.objects.all().order_by('-id')
    if status_filter:
        all_jobs = all_jobs.filter(status=status_filter)

    pending_jobs = Job.objects.filter(status='pending')
    approved_jobs = Job.objects.filter(status='deposit_paid', assigned_worker__isnull=True)
    workers = User.objects.filter(role='worker')
    customers = User.objects.filter(role='customer')

    return render(request, 'services/dashboards/manager.html', {
        'pending_jobs': pending_jobs,
        'approved_jobs': approved_jobs,
        'all_jobs': all_jobs,
        'workers': workers,
        'customers': customers,
        'selected_status': status_filter
    })


@login_required
def ceo_impersonate_user(request, user_id):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
       
    target_user = get_object_or_404(User, id=user_id)
    login(request, target_user)
    return redirect('dashboard_router')


@login_required
def finance_dashboard(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
   
    all_quotations = Quotation.objects.all()
    
    # 1. Revenue Calculations
    total_revenue = sum(q.total_amount for q in all_quotations if q.is_approved_by_client)
    total_incoming_prices = sum(q.total_amount for q in all_quotations if not q.is_approved_by_client)
    paid_invoices_count = Invoice.objects.count()
    pending_balances_count = sum(1 for q in all_quotations if q.is_deposit_paid and not q.is_balance_paid)

    # --- 2. LAYERED ON TOP: Overhead & Marketer Commission Computations ---
    all_expenses = JobExpense.objects.all()
    total_overhead_spent = sum(exp.amount_spent for exp in all_expenses)
    total_remaining_expense_balance = sum(exp.remaining_balance for exp in all_expenses)

    # Calculate Marketer Commissions on approved revenue
    site_config = SiteConfiguration.get_solo()
    default_commission_rate = site_config.commission_percentage / Decimal('100.00')

    total_marketer_commissions = Decimal('0.00')
    for q in all_quotations:
        if q.is_approved_by_client:
            customer = q.job.customer
            # Check if customer was referred by a marketer
            if customer.referred_by and customer.referred_by.role == 'marketer':
                marketer = customer.referred_by
                rate = marketer.commission_percentage if marketer.commission_percentage is not None else site_config.commission_percentage
                commission_share = q.total_amount * (rate / Decimal('100.00'))
                total_marketer_commissions += commission_share

    # Net Company Revenue Calculation: Gross Revenue - Overhead Spent - Marketer Commissions
    net_company_revenue = total_revenue - total_overhead_spent - total_marketer_commissions
    # -----------------------------------------------------------------------

    return render(request, 'services/dashboards/finance.html', {
        'total_revenue': total_revenue,
        'total_incoming_prices': total_incoming_prices,
        'paid_invoices_count': paid_invoices_count,
        'pending_balances_count': pending_balances_count,
        'total_overhead_spent': total_overhead_spent,
        'total_remaining_expense_balance': total_remaining_expense_balance,
        'total_marketer_commissions': total_marketer_commissions,
        'net_company_revenue': net_company_revenue,
    })

from django.forms import inlineformset_factory
from .models import QuotationItem # Ensure this is imported at the top of your views.py

@login_required
def finance_quotations_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
    
    approved_jobs = Job.objects.filter(status__in=['approved', 'payment_submitted'])
    pending_quotes = Job.objects.filter(status='quote_rejected')
    completed_jobs_pending_balance = Job.objects.filter(status='balance_payment_submitted')

    if request.method == 'POST':
        if 'create_quote' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            
            quote, created = Quotation.objects.get_or_create(
                job=job,
                defaults={
                    'total_amount': 0.00,
                    'deposit_amount': 0.00,
                    'balance_amount': 0.00
                }
            )
           
            form = QuotationForm(request.POST, request.FILES, instance=quote)

            if form.is_valid():
                quote = form.save(commit=False)
                quote.job = job
                
                # Clear out old line items if updating, then save new ones from dynamic inputs
                quote.items.all().delete()
                
                calculated_subtotal = 0.0
                i = 1
                while f'item_price_{i}' in request.POST:
                    try:
                        desc = request.POST.get(f'item_description_{i}', '')
                        qty = float(request.POST.get(f'item_qty_{i}', 1) or 1)
                        price = float(request.POST.get(f'item_price_{i}', 0) or 0)
                        
                        if price > 0 or desc:
                            QuotationItem.objects.create(
                                quotation=quote,
                                description=desc,
                                quantity=qty,
                                amount=price
                            )
                            calculated_subtotal += qty * price
                    except (ValueError, TypeError):
                        pass
                    i += 1

                # Fallback to standard request subtotal if dynamic rows weren't caught
                if calculated_subtotal > 0:
                    quote.subtotal_amount = calculated_subtotal
                else:
                    quote.subtotal_amount = float(request.POST.get('subtotal_amount', 0.00) or 0.00)

                quote.discount_amount = float(request.POST.get('discount_amount', 0.00) or 0.00)
                quote.vat_amount = float(request.POST.get('vat_amount', 0.00) or 0.00)
                quote.deposit_percentage = float(request.POST.get('deposit_percentage', 50.0) or 50.0)
               
                validity_days = int(request.POST.get('validity_days', 5) or 5)
               
                subtotal = quote.subtotal_amount
                discount = quote.discount_amount
                vat = quote.vat_amount
                
                quote.total_amount = max(0.00, subtotal - discount + vat)
                quote.deposit_amount = (quote.total_amount * quote.deposit_percentage) / 100
                quote.balance_amount = quote.total_amount - quote.deposit_amount
                quote.valid_until = timezone.now() + timedelta(days=validity_days)
               
                if request.FILES.get('quotation_pdf'):
                    quote.quotation_pdf = request.FILES.get('quotation_pdf')
               
                quote.save()
                job.status = 'quote_sent'
                job.save()
                
                messages.success(request, f"Quotation for Job #{job.id} created successfully!")
                return redirect('finance_quotations')
            else:
                messages.error(request, "Please correct the errors in the quotation form.")
                print("--- QUOTATION FORM ERRORS ---", form.errors)
             
        elif 'confirm_partial_payment' in request.POST or 'confirm_payment' in request.POST:
            quote_id = request.POST.get('quote_id')
            quote = get_object_or_404(Quotation, id=quote_id)
            quote.is_deposit_paid = True
            quote.save()
           
            quote.job.status = 'deposit_paid'
            quote.job.save()
            return redirect('finance_quotations')

    return render(request, 'services/dashboards/finance_quotations.html', {
        'approved_jobs': approved_jobs,
        'pending_quotes': pending_quotes,
        'completed_jobs_pending_balance': completed_jobs_pending_balance,
    })

@login_required
def confirm_balance_paid(request, quotation_id):
    """Allows finance or superuser to confirm that the final balance has been paid by the customer."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
        
    quotation = get_object_or_404(Quotation, id=quotation_id)
    
    if request.method == 'POST':
        # Mark balance as paid
        quotation.is_balance_paid = True
        quotation.save()
        
        # Also update the related Job status so the invoice unlocks for the customer
        job = getattr(quotation, 'job', None)
        if job:
            job.status = 'settled' # Matches the allowed invoice status condition
            job.save()
            
            # Archive the completed/settled job automatically now that payment is confirmed
            ServiceJobArchive.objects.get_or_create(
                job_id=job.id,
                defaults={
                    'client_name': f"{job.customer.first_name} {job.customer.last_name} (@{job.customer.username})",
                    'assigned_staff': job.assigned_worker.username if job.assigned_worker else "Unassigned",
                    'job_description': job.description,
                    'job_flow_status': job.get_status_display() if hasattr(job, 'get_status_display') else job.status,
                    'total_amount': quotation.total_amount,
                    'invoice_number': getattr(job, 'invoice', None).invoice_number if hasattr(job, 'invoice') else f"INV-{job.id}",
                    'has_quotation': True,
                    'job_day': job.created_at.strftime('%A'),
                    'job_month': job.created_at.strftime('%B %Y'),
                    'created_at': job.created_at
                }
            )
            
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Balance confirmed successfully! Invoice is now unlocked.'})
            
        return redirect('finance_dashboard')
        
    return redirect('finance_dashboard')


@login_required
def finance_invoices_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
   
    completed_jobs = Job.objects.filter(status='completed', invoice__isnull=True)

    if request.method == 'POST':
        if 'create_invoice' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            invoice_num = f"INV-{job.id}-{random.randint(1000, 9999)}"
            invoice_pdf_file = request.FILES.get('invoice_pdf')
           
            Invoice.objects.create(
                job=job,
                invoice_number=invoice_num,
                invoice_pdf=invoice_pdf_file
            )
            job.status = 'fully_paid'
            job.save()
            
            # Archive job record automatically
            q = getattr(job, 'quotation', None)
            ServiceJobArchive.objects.get_or_create(
                job_id=job.id,
                defaults={
                    'client_name': f"{job.customer.first_name} {job.customer.last_name} (@{job.customer.username})",
                    'assigned_staff': job.assigned_worker.username if job.assigned_worker else "Unassigned",
                    'job_description': job.description,
                    'job_flow_status': job.get_status_display() if hasattr(job, 'get_status_display') else job.status,
                    'total_amount': q.total_amount if q else 0.00,
                    'invoice_number': invoice_num,
                    'has_quotation': bool(q),
                    'job_day': job.created_at.strftime('%A'),
                    'job_month': job.created_at.strftime('%B %Y'),
                    'created_at': job.created_at
                }
            )
            return redirect('finance_invoices')

    return render(request, 'services/dashboards/finance_invoices.html', {
        'completed_jobs': completed_jobs,
    })


@login_required
def worker_dashboard(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'worker':
        return redirect('dashboard_router')
       
    assigned_jobs = Job.objects.filter(assigned_worker=request.user)

    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        new_status = request.POST.get('status')
        job = get_object_or_404(Job, id=job_id, assigned_worker=request.user)
        
        # Valid worker update statuses
        if new_status in ['on_site', 'in_progress', 'completed', 'work_completed']:
            job.status = new_status
            job.save()
            
            # If the request is sent via AJAX/Fetch, return JSON to prevent network/parsing errors
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({'success': True, 'status': job.status})
                
            return redirect('worker_dashboard')
            
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

    return render(request, 'services/dashboards/worker.html', {'assigned_jobs': assigned_jobs})
import resend
import os
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
import resend
import os
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_active = False  # Deactivate until OTP is verified
                user.set_password(form.cleaned_data['password'])
                user.save()
                
                if hasattr(form, 'save_m2m'):
                    form.save_m2m()
                
                # Generate 6-digit OTP
                code = str(random.randint(100000, 999999))
                PasswordResetOTP.objects.filter(user=user).delete()
                PasswordResetOTP.objects.create(user=user, otp_code=code)
                
                # Save user ID in session
                request.session['signup_user_id'] = user.id
                
                # Send email via Resend using your custom environment variable domain sender
                try:
                    resend.api_key = os.environ.get('EMAIL_HOST_PASSWORD')
                    sender_email = os.environ.get('DEFAULT_FROM_EMAIL', 'support@techsni.com.ng')
                    params = {
                        "from": sender_email,
                        "to": [user.email],
                        "subject": "Your Verification Code",
                        "html": f"<p>Hello,</p><p>Your verification code is: <strong>{code}</strong></p><p>Please enter this code to activate your account.</p>"
                    }
                    resend.Emails.send(params)
                except Exception as mail_err:
                    print("EMAIL SENDING FAILED:", str(mail_err))
                
                # Redirect to verification page without storing the code in session
                return redirect('signup_verify_otp')
                
            except Exception as e:
                print("REGISTRATION ERROR:", str(e))
                return render(request, 'services/register.html', {'form': form, 'error': f"An error occurred: {str(e)}"})
        else:
            print("REGISTRATION FORM ERRORS:", form.errors.as_json() if hasattr(form.errors, 'as_json') else form.errors)
            return render(request, 'services/register.html', {'form': form})
    else:
        form = CustomUserRegistrationForm()
        
    return render(request, 'services/register.html', {'form': form})


def verify_signup_otp_view(request):
    user_id = request.session.get('signup_user_id')
    if not user_id:
        return redirect('register')
        
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        entered_code = request.POST.get('otp', '').strip()
        
        # Safely get the latest OTP record using filter instead of get to prevent 500 errors
        otp_record = PasswordResetOTP.objects.filter(user=user).order_by('-id').first()
        
        if otp_record and otp_record.otp_code.strip() == entered_code:
            user.is_active = True
            user.save()
            
            # Clean up token records and session keys
            PasswordResetOTP.objects.filter(user=user).delete()
            
            if 'signup_user_id' in request.session:
                del request.session['signup_user_id']
                
            return redirect('login')
        else:
            return render(request, 'services/verify_signup_otp.html', {'error': 'Invalid or expired OTP code.'})
            
    return render(request, 'services/verify_signup_otp.html')

def check_username(request):
    username = request.GET.get('username', None)
    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'exists': exists})


@login_required
def ceo_jobs_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
       
    if request.method == 'POST':
        if 'approve_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'approved'
            job.save()
            return redirect('ceo_jobs')
        elif 'reject_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'rejected'
            job.save()
            return redirect('ceo_jobs')

    status_filter = request.GET.get('status', '')
    all_jobs = Job.objects.all().order_by('-id')
    if status_filter:
        all_jobs = all_jobs.filter(status=status_filter)

    return render(request, 'services/dashboards/ceo_jobs.html', {
        'all_jobs': all_jobs,
        'selected_status': status_filter
    })


@login_required
def ceo_users_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
       
    users = User.objects.all().order_by('-id')
    return render(request, 'services/dashboards/ceo_users.html', {'users': users})


@login_required
def manager_jobs_view(request):
    request.user.refresh_from_db()
    role = str(request.user.role).strip().lower() if request.user.role else ''
    if not request.user.is_superuser and role not in ['manager', 'general_manager', 'assistant_manager', 'ceo']:
        return redirect('dashboard_router')
       
    if request.method == 'POST':
        if 'approve_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'approved'
            job.save()
            return redirect('manager_jobs')
        elif 'reject_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'rejected'
            job.save()
            return redirect('manager_jobs')

    status_filter = request.GET.get('status', '')
    all_jobs = Job.objects.all().order_by('-id')
    if status_filter:
        all_jobs = all_jobs.filter(status=status_filter)

    return render(request, 'services/dashboards/manager_jobs.html', {
        'all_jobs': all_jobs,
        'selected_status': status_filter
    })





@login_required
def download_quotation_pdf(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if not request.user.is_superuser and request.user.role not in ['ceo', 'finance', 'manager', 'general_manager', 'assistant_manager'] and job.customer != request.user:
        return redirect('dashboard_router')
   
    if hasattr(job, 'quotation') and job.quotation.quotation_pdf:
        return redirect(job.quotation.quotation_pdf.url)
   
    config = SiteConfiguration.get_solo()
    active_bank = CompanyBankAccount.objects.filter(is_active=True).first()
    q = getattr(job, 'quotation', None)
    
    # Safely extract PO details if a purchase order workflow exists for this job
    po_record = getattr(job, 'purchase_order', None)
    
    # Fetch dynamic item rows if they exist, otherwise fallback to standard job info
    quotation_items = q.items.all() if q else []
   
    items_html = ""
    if quotation_items:
        for item in quotation_items:
            line_total = item.get_total()
            # Fixed Serial Number Fallback to prevent 'N/A' when item or job serial exists
            item_serial = getattr(item, 'serial_number', None) or job.serial_number or 'N/A'
            items_html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 12px;">{item.description}</td>
                <td style="padding: 12px; text-align: center;">{item_serial}</td>
                <td style="padding: 12px; text-align: center;">{item.quantity}</td>
                <td style="padding: 12px; text-align: right;">₦{item.amount:,.2f}</td>
                <td style="padding: 12px; text-align: right;">₦{line_total:,.2f}</td>
            </tr>
            """
    else:
        fallback_amt = q.subtotal_amount if q else 0.00
        fallback_serial = job.serial_number or 'N/A'
        items_html = f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 12px;">{job.job_type.name if job.job_type else 'Repair Service'} - {job.model_type or 'General Service'}</td>
            <td style="padding: 12px; text-align: center;">{fallback_serial}</td>
            <td style="padding: 12px; text-align: center;">1</td>
            <td style="padding: 12px; text-align: right;">₦{fallback_amt:,.2f}</td>
            <td style="padding: 12px; text-align: right;">₦{fallback_amt:,.2f}</td>
        </tr>
        """

    # Conditional PO block for client details info section
    po_details_html = ""
    if po_record:
        po_details_html = f"""
        <p style="margin: 3px 0;"><strong>PO Number:</strong> {po_record.po_number or 'N/A'}</p>
        <p style="margin: 3px 0;"><strong>Payment Terms:</strong> {po_record.payment_terms or 'Net 30 Days'}</p>
        <p style="margin: 3px 0;"><strong>PO Due Date:</strong> {po_record.due_date.strftime('%Y-%m-%d') if po_record.due_date else 'N/A'}</p>
        """

    html_content = f"""
    <html>
    <head><title>Quotation #{job.id} - {config.company_name}</title></head>
    <body style="font-family: Arial, sans-serif; padding: 40px; color: #333; max-width: 800px; margin: auto; border: 1px solid #ddd;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: #b30000; margin-bottom: 5px;">{config.company_name}</h1>
                <p style="margin: 0; color: #555;">Official Quotation</p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0;"><strong>Address:</strong> {config.company_address or 'N/A'}</p>
                <p style="margin: 0;"><strong>Phone:</strong> {config.contact_phone or 'N/A'}</p>
                <p style="margin: 0;"><strong>Email:</strong> {config.contact_email or 'N/A'}</p>
            </div>
        </div>
        <hr style="border: 0; border-top: 2px solid #b30000; margin: 20px 0;">
        <table style="width: 100%; margin-bottom: 20px;">
            <tr>
                <td>
                    <p style="margin: 3px 0;"><strong>Billed To:</strong> {job.customer.first_name} {job.customer.last_name} (@{job.customer.username})</p>
                    <p style="margin: 3px 0;"><strong>Address:</strong> {job.customer.address or 'N/A'}, {job.customer.state or ''}</p>
                    {po_details_html}
                </td>
                <td style="text-align: right;">
                    <p style="margin: 3px 0;"><strong>Job Serial ID:</strong> #{job.id}</p>
                    <p style="margin: 3px 0;"><strong>Date Issued:</strong> {q.created_at.strftime('%Y-%m-%d') if q and hasattr(q, 'created_at') else 'N/A'}</p>
                    <p style="margin: 3px 0;"><strong>Valid Until:</strong> {q.valid_until.strftime('%Y-%m-%d') if q and q.valid_until else 'N/A'}</p>
                </td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
            <tr style="background-color: #181a1e; color: white;">
                <th style="padding: 10px; text-align: left;">Item / Model Description</th>
                <th style="padding: 10px; text-align: center;">Serial Number</th>
                <th style="padding: 10px; text-align: center;">Qty</th>
                <th style="padding: 10px; text-align: right;">Unit Price</th>
                <th style="padding: 10px; text-align: right;">Total</th>
            </tr>
            {items_html}
        </table>
        <div style="float: right; width: 320px;">
            <p style="display: flex; justify-content: space-between; margin: 5px 0;"><span>Subtotal:</span> <strong>₦{q.subtotal_amount if q else '0.00'}</strong></p>
            <p style="display: flex; justify-content: space-between; margin: 5px 0; color: #d9534f;"><span>Discount:</span> <strong>-₦{q.discount_amount if q else '0.00'}</strong></p>
            <p style="display: flex; justify-content: space-between; margin: 5px 0;"><span>VAT / Tax:</span> <strong>₦{q.vat_amount if q else '0.00'}</strong></p>
            <hr>
            <p style="display: flex; justify-content: space-between; margin: 5px 0; font-size: 1.1em;"><span>Total Amount:</span> <strong style="color: #b30000;">₦{q.total_amount if q else '0.00'}</strong></p>
            <p style="display: flex; justify-content: space-between; margin: 5px 0;"><span>Deposit Required ({q.deposit_percentage if q else 50}%):</span> <strong>₦{q.deposit_amount if q else '0.00'}</strong></p>
            <p style="display: flex; justify-content: space-between; margin: 5px 0;"><span>Balance Due:</span> <strong>₦{q.balance_amount if q else '0.00'}</strong></p>
        </div>
        <div style="clear: both;"></div>
        
        <div style="margin-top: 30px; padding: 15px; background-color: #f9f9f9; border: 1px solid #eee;">
            <h4 style="margin: 0 0 10px 0; color: #b30000;">Payment Instructions:</h4>
            <p style="margin: 3px 0;"><strong>Bank Name:</strong> {active_bank.bank_name if active_bank else 'No Active Bank Configured'}</p>
            <p style="margin: 3px 0;"><strong>Account Number:</strong> {active_bank.account_number if active_bank else 'N/A'}</p>
            <p style="margin: 3px 0;"><strong>Account Name:</strong> {active_bank.account_name if active_bank else 'N/A'}</p>
        </div>

        <hr style="border: 0; border-top: 1px solid #ddd; margin: 40px 0 20px 0;">
        <p style="text-align: center; font-size: 0.9em; color: #777;">Thank you for doing business with {config.company_name}!</p>
    </body>
    </html>
    """
    return HttpResponse(html_content)

@login_required
def finance_part_payments_view(request):
    """Allows finance or admin to track and manage part payments / installment balances."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
        
    quotations = Quotation.objects.filter(is_approved_by_client=True, is_balance_paid=False)

    if request.method == 'POST':
        quote_id = request.POST.get('quote_id')
        payment_amount = float(request.POST.get('payment_amount', 0.00))
        quote = get_object_or_404(Quotation, id=quote_id)
        
        if payment_amount > 0:
            quote.deposit_amount += payment_amount
            if quote.deposit_amount >= quote.total_amount:
                quote.is_balance_paid = True
                quote.job.status = 'fully_paid'
                quote.job.save()
            quote.save()
            messages.success(request, f"Successfully recorded part payment of ₦{payment_amount}.")
            
        return redirect('finance_part_payments')

    return render(request, 'services/dashboards/finance_part_payments.html', {
        'quotations': quotations
    })


# --- NEW: INSTRUCTION CATALOG VIEW ---
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import InstructionCatalog

def instruction_catalog_view(request):
    """Publicly accessible instruction catalog viewer."""
    catalogs = InstructionCatalog.objects.all()
    return render(request, 'services/instruction_catalogs.html', {
        'catalogs': catalogs
    })

@login_required
def manage_catalogs_view(request):
    """Dashboard view for CEO and Managers to manage catalogs."""
    if request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager'] and not request.user.is_superuser:
        return redirect('gateway')
    
    catalogs = InstructionCatalog.objects.all()
    return render(request, 'services/dashboards/manage_catalogs.html', {
        'catalogs': catalogs
    })

@login_required
def add_catalog_view(request):
    """Add a new instruction catalog item."""
    if request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager'] and not request.user.is_superuser:
        return redirect('gateway')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        order = request.POST.get('order', 0)
        image = request.FILES.get('image')
        pdf_document = request.FILES.get('pdf_document')

        InstructionCatalog.objects.create(
            title=title,
            description=description,
            order=order,
            image=image,
            pdf_document=pdf_document
        )
        return redirect('manage_catalogs')

    return render(request, 'services/dashboards/catalog_form.html', {'action': 'Add'})


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CompanyBankAccount

@login_required
def service_bank_accounts_view(request):
    """Allows the CEO to manage company bank accounts for service invoices and quotations."""
    if not request.user.is_staff and not getattr(request.user, 'is_ceo', False):
        return redirect('service_home')

    if request.method == 'POST':
        bank_name = request.POST.get('bank_name')
        account_number = request.POST.get('account_number')
        account_name = request.POST.get('account_name')
        is_active = True if request.POST.get('is_active') == 'on' else False

        if is_active:
            CompanyBankAccount.objects.all().update(is_active=False)

        CompanyBankAccount.objects.create(
            bank_name=bank_name,
            account_number=account_number,
            account_name=account_name,
            is_active=is_active
        )

        return redirect('service_bank_accounts')

    accounts = CompanyBankAccount.objects.all()
    context = {'accounts': accounts}
    return render(request, 'services/dashboards/bank_accounts.html', context)

import random
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from .models import PasswordResetOTP

User = get_user_model()

def custom_password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            code = str(random.randint(100000, 999999))
            
            PasswordResetOTP.objects.filter(user=user).delete()
            PasswordResetOTP.objects.create(user=user, otp_code=code)
            
            request.session['reset_user_id'] = user.id
            
            # Send the actual email package (which goes to console locally)
            send_mail(
                subject='Your Password Reset OTP Code',
                message=f'Your verification code to reset your password is: {code}',
                from_email='admin@techsni.com',
                recipient_list=[email],
                fail_silently=False,
            )
            
            # Automatically save message to session for local developer mode or standard notification
            if settings.DEBUG:
                request.session['password_reset_success_message'] = f"DEVELOPER MODE OTP: {code}"
            else:
                request.session['password_reset_success_message'] = "An OTP code has been sent to your email address."
                
            return redirect('verify_otp')
            
        except User.DoesNotExist:
            error = "No user found with this email address."
            return render(request, 'services/password_reset_form.html', {'error': error})
            
    return render(request, 'services/password_reset_form.html')

def set_new_password_view(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('password_reset')
        
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            del request.session['reset_user_id']
            return redirect('login')
        else:
            error = "Passwords do not match."
            return render(request, 'services/set_new_password.html', {'error': error})
            
    return render(request, 'services/set_new_password.html')

@login_required
def edit_catalog_view(request, pk):
    """Edit an existing instruction catalog item."""
    if request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager'] and not request.user.is_superuser:
        return redirect('gateway')

    catalog = get_object_or_404(InstructionCatalog, pk=pk)

    if request.method == 'POST':
        catalog.title = request.POST.get('title')
        catalog.description = request.POST.get('description')
        catalog.order = request.POST.get('order', 0)
        
        if request.FILES.get('image'):
            catalog.image = request.FILES.get('image')
        if request.FILES.get('pdf_document'):
            catalog.pdf_document = request.FILES.get('pdf_document')
            
        catalog.save()
        return redirect('manage_catalogs')

    return render(request, 'services/dashboards/catalog_form.html', {'action': 'Edit', 'catalog': catalog})

@login_required
def delete_catalog_view(request, pk):
    """Delete an instruction catalog item."""
    if request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager'] and not request.user.is_superuser:
        return redirect('gateway')

    catalog = get_object_or_404(InstructionCatalog, pk=pk)
    catalog.delete()
    return redirect('manage_catalogs')


@login_required
def export_service_history_excel(request):
    """Exports archived job records as a downloadable CSV file."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager', 'finance']:
        return redirect('dashboard_router')
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="service_job_history.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Job ID', 'Client Name', 'Assigned Staff', 'Description', 'Status', 'Total Amount', 'Invoice Number', 'Created At'])
    
    archives = ServiceJobArchive.objects.all().order_by('-created_at')
    for arc in archives:
        writer.writerow([
            arc.job_id,
            arc.client_name,
            arc.assigned_staff,
            arc.job_description,
            arc.job_flow_status,
            arc.total_amount,
            arc.invoice_number,
            arc.created_at
        ])
        
    return response

def about_us_view(request):
    """Renders the About Us page."""
    if request.user.is_authenticated:
        request.user.refresh_from_db()
    config = SiteConfiguration.get_solo()
    return render(request, 'services/about_us.html', {
        'config': config
    })

def company_policy_view(request):
    """Renders the Company Policy page."""
    if request.user.is_authenticated:
        request.user.refresh_from_db()
    config = SiteConfiguration.get_solo()
    return render(request, 'services/company_policy.html', {
        'config': config
    })

@login_required
def export_service_history_pdf(request):
    """Exports archived job records as a printable report page."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager', 'finance']:
        return redirect('dashboard_router')
        
    archives = ServiceJobArchive.objects.all().order_by('-created_at')
    
    context = {
        'archives': archives,
    }
    return render(request, 'services/dashboards/service_job_history_pdf.html', context)

@login_required
def update_worker_job_status(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'worker':
        return redirect('dashboard_router')
        
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        new_status = request.POST.get('status')
        job = get_object_or_404(Job, id=job_id, assigned_worker=request.user)
        
        if new_status in ['on_site', 'in_progress', 'completed']:
            job.status = new_status
            job.save()
            
            # If the job is marked as completed, let's make sure any pre-generated PDF cache 
            # is cleared if it's a PO job so that the new PO invoice layout displays dynamically.
            if new_status == 'completed':
                po_record = PurchaseOrderRecord.objects.filter(job=job).first()
                if po_record or getattr(job, 'is_po_job', False):
                    if hasattr(job, 'invoice') and job.invoice and job.invoice.invoice_pdf:
                        # Clear old cached PDF to enforce dynamic PO invoice generation
                        job.invoice.invoice_pdf.delete(save=False)
                        job.invoice.save()

            messages.success(request, f"Job #{job.id} status updated to {job.get_status_display()}.")
            
    return redirect('worker_dashboard')

@login_required
def service_job_history_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager', 'finance']:
        return redirect('dashboard_router')
        
    archives = ServiceJobArchive.objects.all().order_by('-created_at')
    return render(request, 'services/dashboards/service_job_history.html', {
        'archives': archives
    })
@login_required
def marketer_analytics_view(request):
    request.user.refresh_from_db()
    allowed_roles = ['ceo', 'manager', 'general_manager', 'finance']
    if not request.user.is_superuser and getattr(request.user, 'role', None) not in allowed_roles:
        return redirect('dashboard_router')

    from django.contrib.auth import get_user_model
    from decimal import Decimal
    User = get_user_model()

    # Fetch users with the 'marketer' role
    marketers = User.objects.filter(role='marketer') if hasattr(User, 'role') else User.objects.none()

    marketer_stats_raw = []
    grand_total_revenue = Decimal('0.00')

    for marketer in marketers:
        referred_customers = User.objects.filter(referred_by=marketer) if hasattr(User, 'referred_by') else User.objects.none()
        
        total_spend = Decimal('0.00')
        for cust in referred_customers:
            cust_jobs = Job.objects.filter(customer=cust)
            for job in cust_jobs:
                if hasattr(job, 'quotation') and job.quotation and job.quotation.is_approved_by_client:
                    total_spend += job.quotation.total_amount or Decimal('0.00')

        grand_total_revenue += total_spend
        marketer_stats_raw.append({
            'marketer': marketer,
            'customer_count': referred_customers.count(),
            'total_spend': total_spend,
        })

    # Calculate percentage share and estimated commission using proper Decimal arithmetic
    marketer_stats = []
    for item in marketer_stats_raw:
        spend = item['total_spend']
        percentage_share = (float(spend) / float(grand_total_revenue) * 100) if grand_total_revenue > 0 else 0.0
        estimated_commission = spend * Decimal('0.50')  # 50% commission rate as Decimal

        item['percentage_share'] = round(percentage_share, 1)
        item['estimated_commission'] = estimated_commission
        marketer_stats.append(item)

    # Fetch all referred users ledger list
    referred_users = User.objects.filter(referred_by__isnull=False).select_related('referred_by').order_by('-date_joined') if hasattr(User, 'referred_by') else []

    return render(request, 'services/dashboards/marketer_analytics.html', {
        'marketer_stats': marketer_stats,
        'referred_users': referred_users,
    })

@login_required
def edit_site_config_view(request):
    """Allows CEO/Manager to edit About Us, Company Policy, Commission Percentage, and upload PDFs."""
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager']:
        return redirect('dashboard_router')
        
    config = SiteConfiguration.get_solo()
    
    if request.method == 'POST':
        config.company_name = request.POST.get('company_name', config.company_name)
        config.contact_phone = request.POST.get('contact_phone', config.contact_phone)
        config.contact_email = request.POST.get('contact_email', config.contact_email)
        config.about_text = request.POST.get('about_text', '')
        config.policy_text = request.POST.get('policy_text', '')
        
        # --- CAPTURE COMMISSION PERCENTAGE ---
        commission_val = request.POST.get('commission_percentage')
        if commission_val:
            config.commission_percentage = commission_val
        
        if 'about_pdf' in request.FILES:
            config.about_pdf = request.FILES['about_pdf']
        if 'policy_pdf' in request.FILES:
            config.policy_pdf = request.FILES['policy_pdf']
            
        config.save()
        return redirect('dashboard_router')
        
    return render(request, 'services/dashboards/edit_site_config.html', {'config': config})

from .models import Job, Quotation, User, JobType, SiteConfiguration

@login_required
def marketer_dashboard_view(request):
    request.user.refresh_from_db()
    role = str(request.user.role).strip().lower() if request.user.role else ''
    if not request.user.is_superuser and role != 'marketer':
        return redirect('dashboard_router')
        
    # Get all customers referred by this logged-in marketer
    referred_customers = User.objects.filter(referred_by=request.user)
    
    # Calculate total spending by their referred customers
    total_spend = 0
    customer_data = []
    for cust in referred_customers:
        cust_spend = 0
        customer_jobs = Job.objects.filter(customer=cust)
        for j in customer_jobs:
            if hasattr(j, 'quotation') and j.quotation and j.quotation.is_approved_by_client:
                cust_spend += float(j.quotation.total_amount)
        total_spend += cust_spend
        customer_data.append({
            'customer': cust,
            'total_spend': cust_spend
        })
        
    # --- INDIVIDUAL / GLOBAL COMMISSION CALCULATION ---
    config = SiteConfiguration.get_solo()
    if request.user.commission_percentage is not None:
        commission_rate = float(request.user.commission_percentage)
    else:
        commission_rate = float(config.commission_percentage)
        
    estimated_commission = total_spend * (commission_rate / 100)
        
    context = {
        'referred_customers': referred_customers,
        'customer_data': customer_data,
        'total_spend': total_spend,
        'commission_rate': commission_rate,
        'estimated_commission': estimated_commission,
    }
    return render(request, 'services/dashboards/marketer_dashboard.html', context)

import csv
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Job, Quotation, Invoice

@login_required
def finance_part_payments_view(request):
    """
    Displays all jobs where quotations exist, tracking deposits paid, 
    remaining balances, timestamps, and live statuses with filters & export.
    """
    queryset = Job.objects.filter(quotation__isnull=False).select_related('customer', 'job_type', 'quotation')

    # Filtering logic
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    if search_query:
        queryset = queryset.filter(
            Q(id__icontains=search_query) | 
            Q(customer__username__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query)
        )

    # Check if export requested
    export_format = request.GET.get('export', '')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="part_payments_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Job ID', 'Customer', 'Service Type', 'Job Status', 'Quoted Amount', 'Deposit Paid', 'Balance Remaining', 'Job Date'])
        
        for job in queryset:
            quote = getattr(job, 'quotation', None)
            writer.writerow([
                f"#{job.id}",
                job.customer.get_full_name() or job.customer.username,
                job.job_type.name if job.job_type else "N/A",
                job.get_status_display(),
                quote.total_amount if quote else 0.00,
                quote.deposit_amount if (quote and quote.is_deposit_paid) else 0.00,
                quote.balance_amount if quote else 0.00,
                job.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    context = {
        'jobs_list': queryset.order_by('-created_at'),
        'status_choices': Job.STATUS_CHOICES,
        'selected_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }
    return render(request, 'services/dashboards/finance_part_payments.html', context)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Job


@login_required
def finance_invoices_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
   
    jobs = Job.objects.all().select_related('customer', 'invoice').order_by('-id')

    # Auto-generate missing invoices for settled or fully paid jobs
    for job in jobs:
        if job.status in ['settled', 'fully_paid'] and not hasattr(job, 'invoice'):
            invoice_num = f"INV-{job.id}-{random.randint(1000, 9999)}"
            Invoice.objects.get_or_create(
                job=job,
                defaults={'invoice_number': invoice_num}
            )

    all_statuses = Job.objects.values_list('status', flat=True).distinct()
    all_models = Job.objects.values_list('model_type', flat=True).distinct()

    status_filter = request.GET.get('status_filter', '')
    model_filter = request.GET.get('model_filter', '')

    if status_filter:
        jobs = jobs.filter(status=status_filter)
    if model_filter:
        jobs = jobs.filter(model_type=model_filter)

    if request.method == 'POST':
        if 'create_invoice' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            invoice_num = f"INV-{job.id}-{random.randint(1000, 9999)}"
            invoice_pdf_file = request.FILES.get('invoice_pdf')
           
            Invoice.objects.update_or_create(
                job=job,
                defaults={
                    'invoice_number': invoice_num,
                    'invoice_pdf': invoice_pdf_file
                }
            )
            job.status = 'settled'
            job.save()
            return redirect('finance_invoices')

    return render(request, 'services/dashboards/finance_invoices.html', {
        'jobs': jobs,
        'all_statuses': all_statuses,
        'all_models': all_models,
        'status_filter': status_filter,
        'model_filter': model_filter,
    })

@login_required
def download_invoice_pdf(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Restriction: Only allow access if user is authorized or is the customer
    if not request.user.is_superuser and request.user.role not in ['ceo', 'finance', 'manager', 'general_manager', 'assistant_manager'] and job.customer != request.user:
        return redirect('dashboard_router')
    
    # Restriction: Only allow invoice generation if job status is 'completed'
    if job.status.lower() != 'completed':
        return HttpResponse("Invoice is not available until the job status is marked as 'Completed'.", status=403)
   
    if hasattr(job, 'invoice') and job.invoice.invoice_pdf:
        return redirect(job.invoice.invoice_pdf.url)
   
    config = SiteConfiguration.get_solo()
    active_bank = CompanyBankAccount.objects.filter(is_active=True).first()
    inv = getattr(job, 'invoice', None)
    q = getattr(job, 'quotation', None)
    
    # Fetch PurchaseOrderRecord only if it is a PO job
    po_record = PurchaseOrderRecord.objects.filter(job=job).first() if job.is_po_job else None
    
    # Fetch items and fix Serial Number display
    invoice_items = inv.items.all() if (inv and inv.items.exists()) else (q.items.all() if q else [])
    
    items_html = ""
    if invoice_items:
        for item in invoice_items:
            line_total = item.get_total()
            # Use item serial if available, otherwise fallback to job serial
            display_serial = item.serial_number or job.serial_number or 'N/A'
            items_html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 12px;">{item.description}</td>
                <td style="padding: 12px; text-align: center;">{display_serial}</td>
                <td style="padding: 12px; text-align: center;">{item.quantity}</td>
                <td style="padding: 12px; text-align: right;">₦{item.amount:,.2f}</td>
                <td style="padding: 12px; text-align: right;">₦{line_total:,.2f}</td>
            </tr>
            """
    else:
        fallback_amt = (inv.total_amount if inv and inv.total_amount else None) or (q.total_amount if q else 0.00)
        items_html = f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 12px;">{job.job_type.name if job.job_type else 'Repair Service'} - Completed Work</td>
            <td style="padding: 12px; text-align: center;">{job.serial_number or 'N/A'}</td>
            <td style="padding: 12px; text-align: center;">1</td>
            <td style="padding: 12px; text-align: right;">₦{fallback_amt:,.2f}</td>
            <td style="padding: 12px; text-align: right;">₦{fallback_amt:,.2f}</td>
        </tr>
        """

    grand_total = (inv.total_amount if inv and inv.total_amount else None) or (q.total_amount if q else 0.00)

    # Conditional PO block: Only display if it's a PO job AND record exists
    po_details_html = ""
    if job.is_po_job and po_record:
        po_details_html = f"""
        <p style="margin: 3px 0;"><strong>PO Number:</strong> {po_record.po_number or 'N/A'}</p>
        <p style="margin: 3px 0;"><strong>Payment Terms:</strong> {po_record.payment_terms or 'Net 30 Days'}</p>
        <p style="margin: 3px 0;"><strong>PO Due Date:</strong> {po_record.due_date.strftime('%Y-%m-%d') if po_record.due_date else 'N/A'}</p>
        """

    # ... (Rest of your HTML template remains the same, ensuring {po_details_html} is placed where you want it)
    # Ensure you are using the html_content variable with the dynamic items_html and po_details_html rendered inside.

# --- PURCHASE ORDER (PO) & STATEMENT OF ACCOUNT WORKFLOW VIEWS ---
from .models import Invoice, Job, Quotation, User, SiteConfiguration, ServiceJobArchive, InstructionCatalog, CompanyBankAccount, PurchaseOrderRecord, StatementOfAccount
from .models import Invoice, Job, Quotation, User, SiteConfiguration, ServiceJobArchive, InstructionCatalog, CompanyBankAccount, PurchaseOrderRecord, StatementOfAccount
@login_required
def customer_submit_po_view(request, job_id):
    """
    Handles dedicated PO requests from the customer PO sidebar.
    Triggers only when explicitly invoked via the PO workflow route.
    """
    request.user.refresh_from_db()
    if request.user.role != 'customer' and not request.user.is_superuser:
        return redirect('dashboard_router')
        
    job = get_object_or_404(Job, id=job_id, customer=request.user)
    
    if request.method == 'POST':
        po_document = request.FILES.get('po_document')
        payment_terms = request.POST.get('payment_terms', 'Net 30')
        due_date = request.POST.get('due_date')
        
        if po_document:
            # Create or update the PurchaseOrderRecord
            po_record, created = PurchaseOrderRecord.objects.update_or_create(
                job=job,
                defaults={
                    'customer': request.user,
                    'po_document': po_document,
                    'payment_terms': payment_terms,
                    'due_date': due_date if due_date else None,
                    'status': 'pending_finance_review'
                }
            )
            job.status = 'po_submitted'
            job.save()
            
            messages.success(request, "Purchase Order request submitted successfully via the PO portal!")
            return redirect('customer_job_detail', job_id=job.id)
        else:
            messages.error(request, "Please attach a valid PO document to proceed.")
            
    return redirect('customer_job_detail', job_id=job.id)




@login_required
def finance_approve_po_view(request, po_id):
    """
    Finance team / General Manager reviews and forwards the PO to the Executive/CEO dashboard.
    """
    request.user.refresh_from_db()
    allowed_roles = ['finance', 'general_manager']
    if not request.user.is_superuser and request.user.role not in allowed_roles:
        return redirect('dashboard_router')
        
    po_record = get_object_or_404(PurchaseOrderRecord, id=po_id)
    if request.method == 'POST':
        po_record.status = 'pending_executive_approval'
        po_record.save()
        messages.success(request, f"PO #{po_record.id} verified and forwarded to Executive/CEO for final approval.")
        
    return redirect('finance_po_list')


@login_required
def executive_approve_po_view(request, po_id):
    """
    Executive (CEO/GM) final approval view for Purchase Order requests.
    """
    request.user.refresh_from_db()
    allowed_roles = ['ceo', 'general_manager']
    if not request.user.is_superuser and request.user.role not in allowed_roles:
        return redirect('dashboard_router')
        
    po_record = get_object_or_404(PurchaseOrderRecord, id=po_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            po_record.status = 'approved'
            po_record.save()
            po_record.job.status = 'po_approved'
            po_record.job.save()
            messages.success(request, f"PO #{po_record.id} fully approved by Executive.")
        elif action == 'reject':
            po_record.status = 'rejected'
            po_record.save()
            po_record.job.status = 'po_rejected'
            po_record.job.save()
            messages.warning(request, f"PO #{po_record.id} rejected.")
            
    return redirect('finance_po_list')


import csv
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.mail import send_mail
import random
from django.template.loader import render_to_string
from .forms import CustomUserRegistrationForm, JobRequestForm, QuotationForm
from .models import Invoice, Job, Quotation, User, SiteConfiguration, ServiceJobArchive, InstructionCatalog, CompanyBankAccount, PurchaseOrderRecord, StatementOfAccount
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from store.models import StoreOrder

import qrcode
import base64
from io import BytesIO
import requests
import os
from django.conf import settings
from openai import OpenAI

# Initialize OpenAI client safely
client = OpenAI(api_key="sk-proj-YOUR_ACTUAL_KEY_HERE")


def login_view(request):
    catalogs = InstructionCatalog.objects.all().order_by("order")

    # Robust QR Code Generation
    qr_base64 = None
    try:
        portal_url = request.build_absolute_uri()
        if not portal_url:
            portal_url = "http://127.0.0.1:8000/"

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(portal_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        print("--- QR GENERATION EXCEPTION:", e)
        portal_url = "http://127.0.0.1:8000/"
        try:
            img = qrcode.make(portal_url)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        except Exception as inner_e:
            print("--- CRITICAL QR ERROR:", inner_e)
            qr_base64 = None

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard_router")
    else:
        form = AuthenticationForm()

    context = {
        "form": form,
        "catalogs": catalogs,
        "portal_url": portal_url,
        "qr_code_image": qr_base64,
    }
    return render(request, "services/login.html", context)


@login_required
def dashboard_router(request):
    request.user.refresh_from_db()
    user = request.user
    role = str(user.role).strip().lower() if user.role else 'customer'
   
    if user.is_superuser or role == 'ceo':
        return redirect('ceo_dashboard')
    elif role in ['manager', 'general_manager', 'assistant_manager']:
        return redirect('manager_dashboard')
    elif role == 'finance':
        return redirect('finance_dashboard')
    elif role == 'worker':
        return redirect('worker_dashboard')
    elif role == 'marketer':
        return redirect('marketer_dashboard')
    elif role == 'customer_service':
        return redirect('csr_dashboard')
    else:
        return redirect('customer_dashboard')


# --- CSR DASHBOARD VIEW ---
@login_required
def csr_dashboard(request):
    user = request.user
    allowed_roles = ['customer_service', 'ceo', 'general_manager', 'manager', 'assistant_manager']
    if user.role not in allowed_roles and not user.is_superuser:
        return redirect('dashboard_router')

    pending_tickets = SupportTicket.objects.filter(status__in=['pending_agent', 'bot_active'], assigned_agent__isnull=True).order_by('-created_at')
    my_tickets = SupportTicket.objects.filter(assigned_agent=user).exclude(status__in=['resolved', 'closed']).order_by('-updated_at')
    resolved_tickets = SupportTicket.objects.filter(status__in=['resolved', 'closed']).order_by('-updated_at')[:20]

    ratings = TicketRating.objects.filter(agent=user) if user.role == 'customer_service' else TicketRating.objects.all()
    avg_rating = ratings.aggregate(Avg('score'))['score__avg'] or 0.0

    context = {
        'pending_tickets': pending_tickets,
        'my_tickets': my_tickets,
        'resolved_tickets': resolved_tickets,
        'ratings': ratings[:10],
        'avg_rating': round(avg_rating, 1),
    }
    return render(request, 'services/dashboards/csr_dashboard.html', context)


@login_required
def csr_claim_ticket(request, ticket_id):
    if request.user.role not in ['customer_service', 'ceo', 'general_manager', 'manager'] and not request.user.is_superuser:
        return HttpResponseForbidden("Unauthorized")

    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    if not ticket.assigned_agent:
        ticket.assigned_agent = request.user
        ticket.status = 'in_progress'
        ticket.save()
        
        TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            sender_type='agent',
            message=f"Agent {request.user.get_full_name() or request.user.username} has joined the conversation and claimed this ticket."
        )

    return redirect('csr_ticket_detail', ticket_id=ticket.id)


@login_required
def csr_ticket_detail_view(request, ticket_id):
    user = request.user
    allowed_roles = [
        'customer_service',
        'ceo',
        'general_manager',
        'manager',
        'assistant_manager',
    ]
    if user.role not in allowed_roles and not user.is_superuser:
        return redirect('dashboard_router')

    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    messages = ticket.messages.all().order_by('timestamp')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'transcribe_audio' or request.FILES.get('audio'):
            try:
                audio_file = request.FILES.get('audio')
                if audio_file:
                    filename = getattr(audio_file, 'name', 'audio.webm')
                    content_type = getattr(audio_file, 'content_type', 'audio/webm')
                    file_tuple = (filename, audio_file.read(), content_type)

                    transcript = client.audio.transcriptions.create(
                        model='whisper-1', file=file_tuple
                    )
                    transcript_text = (
                        transcript.text
                        if hasattr(transcript, 'text')
                        else str(transcript)
                    )

                    return JsonResponse(
                        {'status': 'success', 'transcript': transcript_text}
                    )
                else:
                    return JsonResponse(
                        {'status': 'error', 'message': 'No audio file found.'},
                        status=400,
                    )
            except Exception as e:
                print('--- TRANSCRIPTION ERROR:', e)
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

        elif action == 'send_message':
            msg_text = request.POST.get('message', '').strip()
            if msg_text:
                TicketMessage.objects.create(
                    ticket=ticket,
                    sender=user,
                    sender_type='agent',
                    message=msg_text,
                )
                if ticket.status == 'pending_agent':
                    ticket.status = 'in_progress'
                    ticket.save()

        elif action == 'resolve_ticket':
            ticket.status = 'resolved'
            ticket.save()
            TicketMessage.objects.create(
                ticket=ticket,
                sender=user,
                sender_type='agent',
                message=(
                    'This support request has been marked as RESOLVED. Thank you for'
                    ' reaching out!'
                ),
            )

        return redirect('csr_ticket_detail', ticket_id=ticket.id)

    context = {
        'ticket': ticket,
        'messages': messages,
    }
    return render(request, 'services/dashboards/csr_ticket_detail.html', context)


@login_required
def customer_support_chat_view(request):
    user = request.user
    active_ticket = SupportTicket.objects.filter(customer=user).exclude(status__in=['resolved', 'closed']).first()

    if request.method == 'POST':
        user_msg = request.POST.get('message', '').strip()
        request_agent = request.POST.get('request_agent', False)

        if not active_ticket:
            active_ticket = SupportTicket.objects.create(
                customer=user,
                subject="General Inquiry / Support Request",
                app_source='service',
                status='bot_active'
            )

        if user_msg:
            TicketMessage.objects.create(
                ticket=active_ticket,
                sender=user,
                sender_type='customer',
                message=user_msg
            )

            if active_ticket.status == 'bot_active':
                msg_lower = user_msg.lower()
                bot_reply = None

                if 'service problem' in msg_lower or 'service' in msg_lower:
                    job_types = JobType.objects.filter(is_active=True).values_list('name', flat=True)
                    services_str = ", ".join(job_types) if job_types else "General Repairs, Tracking, and Quotes"
                    bot_reply = f"🤖 AI Assistant: For our **Service app**, I can help you with: {services_str}. Would you like to check your active job status or speak with an agent?"

                elif 'store problem' in msg_lower or 'store' in msg_lower or 'order' in msg_lower:
                    latest_order = StoreOrder.objects.filter(customer=user).order_by('-created_at').first()
                    if latest_order:
                        bot_reply = f"🤖 AI Assistant: For our **Store app**, your recent order #{latest_order.id} status is '{latest_order.get_status_display()}' (Total: ₦{latest_order.total_amount}). Need help with inventory or payment confirmation?"
                    else:
                        bot_reply = "🤖 AI Assistant: For our **Store app**, I can assist you with product inventory, order inquiries, and checkout. You have no recent store orders found."

                elif 'status' in msg_lower or 'repair' in msg_lower or 'job' in msg_lower:
                    latest_job = Job.objects.filter(customer=user).order_by('-created_at').first()
                    if latest_job:
                        bot_reply = f"🤖 AI Assistant: Your latest job #{latest_job.id} ({latest_job.job_type.name if latest_job.job_type else 'Service'}) is currently set to: '{latest_job.get_status_display()}'."
                    else:
                        bot_reply = "🤖 AI Assistant: You currently have no active service/repair orders on file."
                
                elif 'agent' in msg_lower or 'human' in msg_lower or 'representative' in msg_lower or request_agent:
                    active_ticket.status = 'pending_agent'
                    active_ticket.save()
                    bot_reply = "🤖 AI Assistant: Connecting you to an available Customer Service Representative. Please wait..."
                
                else:
                    bot_reply = "🤖 AI Assistant: I can help you with store issues, service orders, job statuses, or connect you to a live support representative. Type 'Agent' anytime to speak with a human."

                if bot_reply:
                    TicketMessage.objects.create(
                        ticket=active_ticket,
                        sender_type='bot',
                        message=bot_reply
                    )

        return redirect('customer_support_chat')

    messages = active_ticket.messages.all().order_by('timestamp') if active_ticket else []
    
    context = {
        'active_ticket': active_ticket,
        'messages': messages,
    }
    return render(request, 'services/dashboards/customer_support_chat.html', context)


@csrf_exempt
def transcribe_voice_note(request):
  if request.method == 'POST':
    try:
      audio_file = (
          request.FILES.get('audio')
          or request.FILES.get('audio_file')
          or request.FILES.get('file')
          or request.FILES.get('voice')
      )

      if audio_file:
        filename = getattr(audio_file, 'name', 'audio.webm')
        content_type = getattr(audio_file, 'content_type', 'audio/webm')
        file_tuple = (filename, audio_file.read(), content_type)

        transcript = client.audio.transcriptions.create(
            model='whisper-1', file=file_tuple
        )
        transcript_text = (
            transcript.text if hasattr(transcript, 'text') else str(transcript)
        )

        return JsonResponse({'status': 'success', 'transcript': transcript_text})
      else:
        return JsonResponse(
            {
                'status': 'error',
                'message': 'No audio file provided under any expected key.',
            },
            status=400,
        )
    except Exception as e:
      import traceback
      traceback.print_exc()
      return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

  return JsonResponse(
      {'status': 'error', 'message': 'Invalid request method.'}, status=405
  )


@login_required
def rate_support_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id, customer=request.user)
    if request.method == 'POST':
        score = int(request.POST.get('score', 5))
        feedback = request.POST.get('feedback', '').strip()
        
        TicketRating.objects.update_or_create(
            ticket=ticket,
            defaults={
                'customer': request.user,
                'agent': ticket.assigned_agent,
                'score': score,
                'feedback': feedback
            }
        )
        ticket.status = 'closed'
        ticket.save()
        return redirect('customer_dashboard')

    return render(request, 'services/dashboards/rate_ticket.html', {'ticket': ticket})


@login_required
def customer_dashboard(request):
    jobs = Job.objects.filter(customer=request.user).order_by('-id')
    form = JobRequestForm()
    return render(request, 'services/dashboards/customer.html', {'form': form, 'jobs': jobs})


@login_required
def customer_jobs_list_view(request):
    job = Job.objects.filter(customer=request.user).order_by('-id').first()
    if not job:
        return redirect('customer_dashboard')
    return redirect('customer_job_detail', job_id=job.id)

@login_required
def customer_job_detail_view(request, job_id):
    job = get_object_or_404(Job, id=job_id, customer=request.user)
    quotation = getattr(job, 'quotation', None)
    
    # Logic: Only show invoice if status is 'completed' or 'closed'
    invoice = getattr(job, 'invoice', None)
    is_job_finished = job.status in ['completed', 'closed', 'settled']
    
    # Flag for "I Have Paid" button
    show_po_payment_button = job.is_po_job and is_job_finished and job.status != 'settled'

    return render(request, 'services/dashboards/customer_job_detail.html', {
        'job': job,
        'quotation': quotation,
        'invoice': invoice if is_job_finished else None,
        'show_po_payment_button': show_po_payment_button,
    })


@login_required
def submit_job_view(request):
    if request.method == 'POST':
        form = JobRequestForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.customer = request.user
            
            # Explicitly clear out video if any residual data exists
            if hasattr(job, 'video'):
                job.video = None
            
            if job.is_po_job and getattr(job, 'po_number', None):
                job.status = 'po_pending_approval'
            
            job.save()
            form.save_m2m() # Saves any many-to-many relationships if present
            
    return redirect('customer_dashboard')


@login_required
def respond_quote_view(request):
    if request.method == 'POST':
        quote_id = request.POST.get('quote_id')
        action = request.POST.get('action')
        quote = get_object_or_404(Quotation, id=quote_id, job__customer=request.user)
       
        if action == 'approve':
            quote.is_approved_by_client = True
            quote.save()
            
            if quote.job.is_po_job:
                quote.job.status = 'po_approved_pending_work'
            else:
                quote.job.status = 'quote_approved'
            quote.job.save()
            
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', 'No reason provided')
            quote.rejection_reason = reason
            quote.save()
            quote.job.status = 'quote_rejected'
            quote.job.save()
        elif action == 'i_have_paid':
            quote.is_deposit_paid = True
            quote.save()
            quote.job.status = 'payment_submitted'
            quote.job.save()
           
    return redirect('customer_dashboard')


@login_required
def pay_balance_view(request):
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        job = get_object_or_404(Job, id=job_id, customer=request.user)
        if hasattr(job, 'quotation'):
            quote = job.quotation
            job.status = 'balance_payment_submitted'
            job.save()
             
    return redirect('customer_job_detail', job_id=job.id)
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Job, JobExpense

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Job, JobExpense

@login_required
def general_manager_job_expense_view(request, job_id):
    """Restricted strictly to CEO, Superusers, and General Managers to log overhead costs and invoices."""
    request.user.refresh_from_db()
    
    # Restrict access: Allow Superuser, CEO role, or General Manager role
    if not request.user.is_superuser and request.user.role not in ['ceo', 'general_manager']:
        messages.error(request, "Access denied. This section is strictly restricted to Executives and General Managers.")
        return redirect('dashboard_router')

    job = get_object_or_404(Job, id=job_id)
    
    # Fetch existing expense record if it exists, or initialize a blank one
    expense_record, created = JobExpense.objects.get_or_create(job=job)

    if request.method == 'POST':
        amount_spent = request.POST.get('amount_spent', '0.00')
        remaining_balance = request.POST.get('remaining_balance', '0.00')
        invoice_note = request.POST.get('invoice_number_or_note')
        transfer_invoice = request.FILES.get('transfer_invoice')

        expense_record.amount_spent = amount_spent
        expense_record.remaining_balance = remaining_balance
        expense_record.invoice_number_or_note = invoice_note
        
        if transfer_invoice:
            expense_record.transfer_invoice = transfer_invoice
            
        expense_record.logged_by = request.user
        expense_record.save()

        messages.success(request, f"Overhead expenses and invoice updated successfully for Job #{job.id}!")
        return redirect('general_manager_job_expense_view', job_id=job.id)

    return render(request, 'services/dashboards/general_manager_expense.html', {
        'job': job,
        'expense_record': expense_record,
    })

@login_required
def ceo_dashboard(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
       
    if request.method == 'POST':
        if 'approve_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'approved'
            job.save()
            return redirect('ceo_dashboard')
        elif 'reject_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'rejected'
            job.save()
            return redirect('ceo_dashboard')

    status_filter = request.GET.get('status', '')
    all_jobs = Job.objects.all().order_by('-id')
    if status_filter:
        all_jobs = all_jobs.filter(status=status_filter)

    live_jobs = Job.objects.all().order_by('-id')
    users = User.objects.all().order_by('-id')
    workers = User.objects.filter(role='worker')

    return render(request, 'services/dashboards/ceo.html', {
        'live_jobs': live_jobs,
        'all_jobs': all_jobs,
        'users': users,
        'workers': workers,
        'selected_status': status_filter
    })


@login_required
def ceo_site_settings_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
        
    config, created = SiteConfiguration.objects.get_or_create(id=1)

    if request.method == 'POST':
        form = SiteConfigurationForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Company site settings updated successfully!")
            return redirect('ceo_site_settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SiteConfigurationForm(instance=config)

    return render(request, 'services/dashboards/ceo_site_settings.html', {
        'form': form,
        'config': config
    })


@login_required
def ceo_update_user_role(request, user_id):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
        
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        valid_roles = ['ceo', 'manager', 'general_manager', 'assistant_manager', 'finance', 'customer_service', 'worker', 'customer', 'marketer']
        
        if new_role in valid_roles:
            target_user.role = new_role
            target_user.save()
            messages.success(request, f"Updated {target_user.username}'s role to {new_role}.")
            
            if new_role == 'marketer':
                store_api_url = 'https://your-store-app-url.com/api/sync-marketer/'
                payload = {
                    'email': target_user.email,
                    'username': target_user.username,
                    'first_name': target_user.first_name,
                    'last_name': target_user.last_name,
                    'role': 'marketer'
                }
                try:
                    response = requests.post(store_api_url, data=payload, timeout=5)
                    if response.status_code == 200:
                        messages.success(request, f"Successfully synced {target_user.username} as a marketer to the Store app.")
                except requests.exceptions.RequestException:
                    messages.warning(request, "Role updated locally, but failed to sync to store app automatically.")

    return redirect(request.META.get('HTTP_REFERER', 'ceo_users'))


@login_required
def ceo_update_user_commission(request, user_id):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager']:
        return redirect('dashboard_router')
        
    target_user = get_object_or_404(User, id=user_id, role='marketer')
    
    if request.method == 'POST':
        commission_input = request.POST.get('commission_percentage', '').strip()
        
        if commission_input == '':
            target_user.commission_percentage = None
            messages.success(request, f"Cleared custom commission for {target_user.username}.")
        else:
            try:
                rate = float(commission_input)
                if 0 <= rate <= 100:
                    target_user.commission_percentage = rate
                    messages.success(request, f"Successfully updated custom commission to {rate}%!")
                else:
                    messages.error(request, "Commission percentage must be between 0 and 100.")
            except ValueError:
                messages.error(request, "Invalid commission percentage format.")
                
        target_user.save()

    return redirect(request.META.get('HTTP_REFERER', 'ceo_users'))


@login_required
def ceo_admin_shortcut_view(request):
    request.user.refresh_from_db()
    if request.user.is_superuser or request.user.role == 'ceo':
        if not request.user.is_staff:
            request.user.is_staff = True
            request.user.save()
        return redirect('/admin/')
    return redirect('dashboard_router')


@login_required
def manager_dashboard(request):
    request.user.refresh_from_db()
    role = str(request.user.role).strip().lower() if request.user.role else ''
    if not request.user.is_superuser and role not in ['manager', 'general_manager', 'assistant_manager', 'ceo']:
        return redirect('dashboard_router')
   
    if request.method == 'POST':
        if 'approve_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'approved'
            job.save()
            return redirect('manager_dashboard')
        elif 'reject_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'rejected'
            job.save()
            return redirect('manager_dashboard')
        elif 'assign_job' in request.POST:
            job_id = request.POST.get('job_id')
            worker_id = request.POST.get('worker_id')
            job = get_object_or_404(Job, id=job_id)
            worker = get_object_or_404(User, id=worker_id, role='worker')
            job.assigned_worker = worker
            job.status = 'on_site'
            job.save()
            return redirect('manager_dashboard')

    status_filter = request.GET.get('status', '')
    all_jobs = Job.objects.all().order_by('-id')
    if status_filter:
        all_jobs = all_jobs.filter(status=status_filter)

    pending_jobs = Job.objects.filter(status__in=['pending', 'po_pending_approval'])
    approved_jobs = Job.objects.filter(status__in=['deposit_paid', 'po_approved_pending_work', 'approved'], assigned_worker__isnull=True)
    workers = User.objects.filter(role='worker')
    customers = User.objects.filter(role='customer')

    return render(request, 'services/dashboards/manager.html', {
        'pending_jobs': pending_jobs,
        'approved_jobs': approved_jobs,
        'all_jobs': all_jobs,
        'workers': workers,
        'customers': customers,
        'selected_status': status_filter
    })


@login_required
def ceo_impersonate_user(request, user_id):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
        
    target_user = get_object_or_404(User, id=user_id)
    login(request, target_user)
    return redirect('dashboard_router')


@login_required
def finance_dashboard(request):
    request.user.refresh_from_db()
    # Allow Superuser, CEO role, or Finance role
    if not request.user.is_superuser and request.user.role not in ['ceo', 'finance']:
        return redirect('dashboard_router')
   
    all_quotations = Quotation.objects.all()
    
    # 1. Revenue Calculations
    total_revenue = sum(q.total_amount for q in all_quotations if q.is_approved_by_client)
    total_incoming_prices = sum(q.total_amount for q in all_quotations if not q.is_approved_by_client)
    paid_invoices_count = Invoice.objects.count()
    pending_balances_count = sum(1 for q in all_quotations if q.is_deposit_paid and not q.is_balance_paid)

    # 2. Overhead & Marketer Commission Computations
    all_expenses = JobExpense.objects.all()
    total_overhead_spent = sum(exp.amount_spent for exp in all_expenses)
    total_remaining_expense_balance = sum(exp.remaining_balance for exp in all_expenses)

    # Calculate Marketer Commissions on approved revenue
    site_config = SiteConfiguration.get_solo()
    total_marketer_commissions = Decimal('0.00')
    
    for q in all_quotations:
        if q.is_approved_by_client:
            customer = q.job.customer
            if customer.referred_by and customer.referred_by.role == 'marketer':
                marketer = customer.referred_by
                rate = marketer.commission_percentage if marketer.commission_percentage is not None else site_config.commission_percentage
                commission_share = q.total_amount * (rate / Decimal('100.00'))
                total_marketer_commissions += commission_share

    # Net Company Revenue Calculation: Gross Revenue - Overhead Spent - Marketer Commissions
    net_company_revenue = total_revenue - total_overhead_spent - total_marketer_commissions

    return render(request, 'services/dashboards/finance.html', {
        'total_revenue': total_revenue,
        'total_incoming_prices': total_incoming_prices,
        'paid_invoices_count': paid_invoices_count,
        'pending_balances_count': pending_balances_count,
        'total_overhead_spent': total_overhead_spent,
        'total_remaining_expense_balance': total_remaining_expense_balance,
        'total_marketer_commissions': total_marketer_commissions,
        'net_company_revenue': net_company_revenue,
    })


@login_required
def finance_quotations_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
    
    approved_jobs = Job.objects.filter(status__in=['approved', 'payment_submitted', 'po_pending_approval'])
    pending_quotes = Job.objects.filter(status='quote_rejected')
    completed_jobs_pending_balance = Job.objects.filter(status='balance_payment_submitted')

    if request.method == 'POST':
        if 'create_quote' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            
            quote, created = Quotation.objects.get_or_create(
                job=job,
                defaults={
                    'total_amount': 0.00,
                    'deposit_amount': 0.00,
                    'balance_amount': 0.00
                }
            )
           
            form = QuotationForm(request.POST, request.FILES, instance=quote)

            if form.is_valid():
                quote = form.save(commit=False)
                quote.job = job
                
                quote.items.all().delete()
                
                calculated_subtotal = 0.0
                i = 1
                while f'item_price_{i}' in request.POST:
                    try:
                        desc = request.POST.get(f'item_description_{i}', '')
                        qty = float(request.POST.get(f'item_qty_{i}', 1) or 1)
                        price = float(request.POST.get(f'item_price_{i}', 0) or 0)
                        
                        if price > 0 or desc:
                            QuotationItem.objects.create(
                                quotation=quote,
                                description=desc,
                                quantity=qty,
                                amount=price
                            )
                            calculated_subtotal += qty * price
                    except (ValueError, TypeError):
                        pass
                    i += 1

                if calculated_subtotal > 0:
                    quote.subtotal_amount = calculated_subtotal
                else:
                    quote.subtotal_amount = float(request.POST.get('subtotal_amount', 0.00) or 0.00)

                quote.discount_amount = float(request.POST.get('discount_amount', 0.00) or 0.00)
                quote.vat_amount = float(request.POST.get('vat_amount', 0.00) or 0.00)
                quote.deposit_percentage = float(request.POST.get('deposit_percentage', 50.0) or 50.0)
               
                validity_days = int(request.POST.get('validity_days', 5) or 5)
               
                subtotal = quote.subtotal_amount
                discount = quote.discount_amount
                vat = quote.vat_amount
                
                quote.total_amount = max(0.00, subtotal - discount + vat)
                quote.deposit_amount = (quote.total_amount * quote.deposit_percentage) / 100
                quote.balance_amount = quote.total_amount - quote.deposit_amount
                quote.valid_until = timezone.now() + timedelta(days=validity_days)
               
                if request.FILES.get('quotation_pdf'):
                    quote.quotation_pdf = request.FILES.get('quotation_pdf')
               
                quote.save()
                job.status = 'quote_sent'
                job.save()
                
                messages.success(request, f"Quotation for Job #{job.id} created successfully!")
                return redirect('finance_quotations')
             
        elif 'confirm_partial_payment' in request.POST or 'confirm_payment' in request.POST:
            quote_id = request.POST.get('quote_id')
            quote = get_object_or_404(Quotation, id=quote_id)
            quote.is_deposit_paid = True
            quote.save()
           
            quote.job.status = 'deposit_paid'
            quote.job.save()
            return redirect('finance_quotations')

    return render(request, 'services/dashboards/finance_quotations.html', {
        'approved_jobs': approved_jobs,
        'pending_quotes': pending_quotes,
        'completed_jobs_pending_balance': completed_jobs_pending_balance,
    })


@login_required
def confirm_balance_paid(request, quotation_id):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
        
    quotation = get_object_or_404(Quotation, id=quotation_id)
    
    if request.method == 'POST':
        quotation.is_balance_paid = True
        quotation.save()
        
        job = getattr(quotation, 'job', None)
        if job:
            job.status = 'settled'
            job.save()
            
            ServiceJobArchive.objects.get_or_create(
                job_id=job.id,
                defaults={
                    'client_name': f"{job.customer.first_name} {job.customer.last_name} (@{job.customer.username})",
                    'assigned_staff': job.assigned_worker.username if job.assigned_worker else "Unassigned",
                    'job_description': job.description,
                    'job_flow_status': job.get_status_display() if hasattr(job, 'get_status_display') else job.status,
                    'total_amount': quotation.total_amount,
                    'invoice_number': getattr(job, 'invoice', None).invoice_number if hasattr(job, 'invoice') else f"INV-{job.id}",
                    'has_quotation': True,
                    'job_day': job.created_at.strftime('%A'),
                    'job_month': job.created_at.strftime('%B %Y'),
                    'created_at': job.created_at
                }
            )
            
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Balance confirmed successfully! Invoice is now unlocked.'})
            
    return redirect('finance_dashboard')


@login_required
def worker_dashboard(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'worker':
        return redirect('dashboard_router')
       
    assigned_jobs = Job.objects.filter(assigned_worker=request.user)

    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        new_status = request.POST.get('status')
        job = get_object_or_404(Job, id=job_id, assigned_worker=request.user)
        
        if new_status in ['on_site', 'in_progress', 'completed', 'work_completed']:
            job.status = new_status
            job.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({'success': True, 'status': job.status})
                
            return redirect('worker_dashboard')
            
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

    return render(request, 'services/dashboards/worker.html', {'assigned_jobs': assigned_jobs})



def check_username(request):
    username = request.GET.get('username', None)
    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'exists': exists})


@login_required
def ceo_jobs_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
       
    if request.method == 'POST':
        if 'approve_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'approved'
            job.save()
            return redirect('ceo_jobs')
        elif 'reject_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'rejected'
            job.save()
            return redirect('ceo_jobs')

    status_filter = request.GET.get('status', '')
    all_jobs = Job.objects.all().order_by('-id')
    if status_filter:
        all_jobs = all_jobs.filter(status=status_filter)

    return render(request, 'services/dashboards/ceo_jobs.html', {
        'all_jobs': all_jobs,
        'selected_status': status_filter
    })


@login_required
def ceo_users_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'ceo':
        return redirect('dashboard_router')
       
    users = User.objects.all().order_by('-id')
    return render(request, 'services/dashboards/ceo_users.html', {'users': users})

@login_required
def manager_jobs_view(request):
    request.user.refresh_from_db()
    role = str(request.user.role).strip().lower() if request.user.role else ''
    if not request.user.is_superuser and role not in ['manager', 'general_manager', 'assistant_manager', 'ceo']:
        return redirect('dashboard_router')
       
    if request.method == 'POST':
        if 'approve_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'approved'
            job.save()
            return redirect('manager_jobs')
        elif 'reject_job' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.status = 'rejected'
            job.save()
            return redirect('manager_jobs')

    status_filter = request.GET.get('status', '')
    all_jobs = Job.objects.all().order_by('-id')
    if status_filter:
        all_jobs = all_jobs.filter(status=status_filter)

    return render(request, 'services/dashboards/manager_jobs.html', {
        'all_jobs': all_jobs,
        'selected_status': status_filter
    })


@login_required
def download_quotation_pdf(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if not request.user.is_superuser and request.user.role not in ['ceo', 'finance', 'manager', 'general_manager', 'assistant_manager'] and job.customer != request.user:
        return redirect('dashboard_router')
   
    if hasattr(job, 'quotation') and job.quotation.quotation_pdf:
        return redirect(job.quotation.quotation_pdf.url)
   
    config = SiteConfiguration.get_solo()
    active_bank = CompanyBankAccount.objects.filter(is_active=True).first()
    q = getattr(job, 'quotation', None)
    
    quotation_items = q.items.all() if q else []
   
    items_html = ""
    if quotation_items:
        for item in quotation_items:
            line_total = item.get_total()
            items_html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 12px;">{item.description}</td>
                <td style="padding: 12px; text-align: center;">{item.serial_number or 'N/A'}</td>
                <td style="padding: 12px; text-align: center;">{item.quantity}</td>
                <td style="padding: 12px; text-align: right;">₦{item.amount:,.2f}</td>
                <td style="padding: 12px; text-align: right;">₦{line_total:,.2f}</td>
            </tr>
            """
    else:
        fallback_amt = q.subtotal_amount if q else 0.00
        items_html = f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 12px;">{job.job_type.name if job.job_type else 'Repair Service'} - {job.model_type or 'General Service'}</td>
            <td style="padding: 12px; text-align: center;">{job.serial_number or 'N/A'}</td>
            <td style="padding: 12px; text-align: center;">1</td>
            <td style="padding: 12px; text-align: right;">₦{fallback_amt:,.2f}</td>
            <td style="padding: 12px; text-align: right;">₦{fallback_amt:,.2f}</td>
        </tr>
        """

    html_content = f"""
    <html>
    <head><title>Quotation #{job.id} - {config.company_name}</title></head>
    <body style="font-family: Arial, sans-serif; padding: 40px; color: #333; max-width: 800px; margin: auto; border: 1px solid #ddd;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: #b30000; margin-bottom: 5px;">{config.company_name}</h1>
                <p style="margin: 0; color: #555;">Official Quotation</p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0;"><strong>Address:</strong> {config.company_address or 'N/A'}</p>
                <p style="margin: 0;"><strong>Phone:</strong> {config.contact_phone or 'N/A'}</p>
                <p style="margin: 0;"><strong>Email:</strong> {config.contact_email or 'N/A'}</p>
            </div>
        </div>
        <hr style="border: 0; border-top: 2px solid #b30000; margin: 20px 0;">
        <table style="width: 100%; margin-bottom: 20px;">
            <tr>
                <td>
                    <p><strong>Billed To:</strong> {job.customer.first_name} {job.customer.last_name} (@{job.customer.username})</p>
                    <p><strong>Address:</strong> {job.customer.address or 'N/A'}, {job.customer.state or ''}</p>
                    {'<p><strong>PO Number:</strong> ' + job.po_number + '</p>' if job.is_po_job and job.po_number else ''}
                </td>
                <td style="text-align: right;">
                    <p><strong>Job Serial ID:</strong> #{job.id}</p>
                    <p><strong>Date Issued:</strong> {q.created_at.strftime('%Y-%m-%d') if q else 'N/A'}</p>
                    <p><strong>Valid Until:</strong> {q.valid_until.strftime('%Y-%m-%d') if q and q.valid_until else 'N/A'}</p>
                </td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
            <tr style="background-color: #181a1e; color: white;">
                <th style="padding: 10px; text-align: left;">Item / Model Description</th>
                <th style="padding: 10px; text-align: center;">Serial Number</th>
                <th style="padding: 10px; text-align: center;">Qty</th>
                <th style="padding: 10px; text-align: right;">Unit Price</th>
                <th style="padding: 10px; text-align: right;">Total</th>
            </tr>
            {items_html}
        </table>
        <div style="float: right; width: 320px;">
            <p style="display: flex; justify-content: space-between; margin: 5px 0;"><span>Subtotal:</span> <strong>₦{q.subtotal_amount if q else '0.00'}</strong></p>
            <p style="display: flex; justify-content: space-between; margin: 5px 0; color: #d9534f;"><span>Discount:</span> <strong>-₦{q.discount_amount if q else '0.00'}</strong></p>
            <p style="display: flex; justify-content: space-between; margin: 5px 0;"><span>VAT / Tax:</span> <strong>₦{q.vat_amount if q else '0.00'}</strong></p>
            <hr>
            <p style="display: flex; justify-content: space-between; margin: 5px 0; font-size: 1.1em;"><span>Total Amount:</span> <strong style="color: #b30000;">₦{q.total_amount if q else '0.00'}</strong></p>
        </div>
        <div style="clear: both;"></div>
        
        <div style="margin-top: 30px; padding: 15px; background-color: #f9f9f9; border: 1px solid #eee;">
            <h4 style="margin: 0 0 10px 0; color: #b30000;">Payment Instructions:</h4>
            <p style="margin: 3px 0;"><strong>Bank Name:</strong> {active_bank.bank_name if active_bank else 'No Active Bank Configured'}</p>
            <p style="margin: 3px 0;"><strong>Account Number:</strong> {active_bank.account_number if active_bank else 'N/A'}</p>
            <p style="margin: 3px 0;"><strong>Account Name:</strong> {active_bank.account_name if active_bank else 'N/A'}</p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)


@login_required
def assign_worker_ajax_view(request):
    request.user.refresh_from_db()
    role = str(request.user.role).strip().lower() if request.user.role else ''
    if not request.user.is_superuser and role not in ['ceo', 'manager', 'general_manager', 'assistant_manager']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Unauthorized action.'}, status=403)
        return redirect('dashboard_router')

    if request.method == 'POST':
        job_id = request.POST.get('job') or request.POST.get('job_id')
        worker_id = request.POST.get('worker') or request.POST.get('worker_id')
        
        job = get_object_or_404(Job, id=job_id)
        
        # --- LAYERED ON TOP: PO Gatekeeper Check ---
        # If it's a PO job, check that the PO record has been fully approved by Finance/Execs
        if getattr(job, 'is_po_job', False):
            po_record = PurchaseOrderRecord.objects.filter(job=job).first()
            if not po_record or po_record.status != 'approved':
                error_msg = 'Cannot assign worker: Corporate PO approval is still pending.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('assign_worker')
        # -------------------------------------------
        
        worker = get_object_or_404(User, id=worker_id, role='worker')
        
        job.assigned_worker = worker
        job.status = 'on_site'
        job.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Worker {worker.username} successfully assigned to Job #{job.id}!',
                'job_id': job.id,
                'worker_name': worker.username,
                'status': job.get_status_display() if hasattr(job, 'get_status_display') else job.status
            })
            
        return redirect('assign_worker')

    active_assignments = Job.objects.exclude(assigned_worker__isnull=True).order_by('-id')
    workers = User.objects.filter(role='worker')
    # Filtered to ensure managers only see jobs that are ready for assignment
    all_jobs = Job.objects.filter(status__in=['approved', 'deposit_paid', 'on_site', 'po_approved_pending_work', 'quote_approved'])

    return render(request, 'services/dashboards/assign_worker.html', {
        'workers': workers,
        'all_jobs': all_jobs,
        'active_assignments': active_assignments
    })

# --- NEW: INSTRUCTION CATALOG VIEWS ---
def instruction_catalog_view(request):
    """Publicly accessible instruction catalog viewer."""
    catalogs = InstructionCatalog.objects.all()
    return render(request, 'services/instruction_catalogs.html', {
        'catalogs': catalogs
    })


@login_required
def manage_catalogs_view(request):
    """Dashboard view for CEO and Managers to manage catalogs."""
    if request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager'] and not request.user.is_superuser:
        return redirect('gateway')
    
    catalogs = InstructionCatalog.objects.all()
    return render(request, 'services/dashboards/manage_catalogs.html', {
        'catalogs': catalogs
    })


@login_required
def add_catalog_view(request):
    """Add a new instruction catalog item."""
    if request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager'] and not request.user.is_superuser:
        return redirect('gateway')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        order = request.POST.get('order', 0)
        image = request.FILES.get('image')
        pdf_document = request.FILES.get('pdf_document')

        InstructionCatalog.objects.create(
            title=title,
            description=description,
            order=order,
            image=image,
            pdf_document=pdf_document
        )
        return redirect('manage_catalogs')

    return render(request, 'services/dashboards/catalog_form.html', {'action': 'Add'})


@login_required
def edit_catalog_view(request, pk):
    """Edit an existing instruction catalog item."""
    if request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager'] and not request.user.is_superuser:
        return redirect('gateway')

    catalog = get_object_or_404(InstructionCatalog, pk=pk)

    if request.method == 'POST':
        catalog.title = request.POST.get('title')
        catalog.description = request.POST.get('description')
        catalog.order = request.POST.get('order', 0)
        
        if request.FILES.get('image'):
            catalog.image = request.FILES.get('image')
        if request.FILES.get('pdf_document'):
            catalog.pdf_document = request.FILES.get('pdf_document')
            
        catalog.save()
        return redirect('manage_catalogs')

    return render(request, 'services/dashboards/catalog_form.html', {'action': 'Edit', 'catalog': catalog})


@login_required
def delete_catalog_view(request, pk):
    """Delete an instruction catalog item."""
    if request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager'] and not request.user.is_superuser:
        return redirect('gateway')

    catalog = get_object_or_404(InstructionCatalog, pk=pk)
    catalog.delete()
    return redirect('manage_catalogs')


# --- BANK ACCOUNTS & PASSWORD RESET VIEWS ---
@login_required
def service_bank_accounts_view(request):
    """Allows the CEO to manage company bank accounts for service invoices and quotations."""
    if not request.user.is_staff and not getattr(request.user, 'is_ceo', False):
        return redirect('service_home')

    if request.method == 'POST':
        bank_name = request.POST.get('bank_name')
        account_number = request.POST.get('account_number')
        account_name = request.POST.get('account_name')
        is_active = True if request.POST.get('is_active') == 'on' else False

        if is_active:
            CompanyBankAccount.objects.all().update(is_active=False)

        CompanyBankAccount.objects.create(
            bank_name=bank_name,
            account_number=account_number,
            account_name=account_name,
            is_active=is_active
        )

        return redirect('service_bank_accounts')

    accounts = CompanyBankAccount.objects.all()
    context = {'accounts': accounts}
    return render(request, 'services/dashboards/bank_accounts.html', context)


def custom_password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            code = str(random.randint(100000, 999999))
            
            PasswordResetOTP.objects.filter(user=user).delete()
            PasswordResetOTP.objects.create(user=user, otp_code=code)
            
            request.session['reset_user_id'] = user.id
            
            send_mail(
                subject='Your Password Reset OTP Code',
                message=f'Your verification code to reset your password is: {code}',
                from_email='admin@techsni.com',
                recipient_list=[email],
                fail_silently=False,
            )
            
            if settings.DEBUG:
                request.session['password_reset_success_message'] = f"DEVELOPER MODE OTP: {code}"
            else:
                request.session['password_reset_success_message'] = "An OTP code has been sent to your email address."
                
            return redirect('verify_otp')
            
        except User.DoesNotExist:
            error = "No user found with this email address."
            return render(request, 'services/password_reset_form.html', {'error': error})
            
    return render(request, 'services/password_reset_form.html')


def verify_otp_view(request):
    if request.method == 'POST':
        entered_code = request.POST.get('otp_code')
        user_id = request.session.get('reset_user_id')
        
        if not user_id:
            return redirect('password_reset')
            
        try:
            user = User.objects.get(id=user_id)
            otp_record = PasswordResetOTP.objects.get(user=user)
            
            if otp_record.is_valid() and otp_record.otp_code == entered_code:
                otp_record.delete()
                if 'password_reset_success_message' in request.session:
                    del request.session['password_reset_success_message']
                return redirect('set_new_password')
            else:
                error = "Invalid or expired OTP code."
                return render(request, 'services/verify_otp.html', {'error': error})
        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            error = "Invalid request session."
            return render(request, 'services/verify_otp.html', {'error': error})
            
    return render(request, 'services/verify_otp.html')


def set_new_password_view(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('password_reset')
        
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            del request.session['reset_user_id']
            return redirect('login')
        else:
            error = "Passwords do not match."
            return render(request, 'services/set_new_password.html', {'error': error})
            
    return render(request, 'services/set_new_password.html')


# --- EXPORT & HISTORY VIEWS ---
@login_required
def export_service_history_excel(request):
    """Exports archived job records as a downloadable CSV file."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager', 'finance']:
        return redirect('dashboard_router')
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="service_job_history.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Job ID', 'Client Name', 'Assigned Staff', 'Description', 'Status', 'Total Amount', 'Invoice Number', 'Created At'])
    
    archives = ServiceJobArchive.objects.all().order_by('-created_at')
    for arc in archives:
        writer.writerow([
            arc.job_id,
            arc.client_name,
            arc.assigned_staff,
            arc.job_description,
            arc.job_flow_status,
            arc.total_amount,
            arc.invoice_number,
            arc.created_at
        ])
        
    return response


def about_us_view(request):
    """Renders the About Us page."""
    if request.user.is_authenticated:
        request.user.refresh_from_db()
    config = SiteConfiguration.get_solo()
    return render(request, 'services/about_us.html', {
        'config': config
    })


def company_policy_view(request):
    """Renders the Company Policy page."""
    if request.user.is_authenticated:
        request.user.refresh_from_db()
    config = SiteConfiguration.get_solo()
    return render(request, 'services/company_policy.html', {
        'config': config
    })


@login_required
def export_service_history_pdf(request):
    """Exports archived job records as a printable report page."""
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager', 'finance']:
        return redirect('dashboard_router')
        
    archives = ServiceJobArchive.objects.all().order_by('-created_at')
    context = {
        'archives': archives,
    }
    return render(request, 'services/dashboards/service_job_history_pdf.html', context)


@login_required
def update_worker_job_status(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'worker':
        return redirect('dashboard_router')
        
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        new_status = request.POST.get('status')
        job = get_object_or_404(Job, id=job_id, assigned_worker=request.user)
        if new_status in ['on_site', 'in_progress', 'completed']:
            job.status = new_status
            job.save()
            messages.success(request, f"Job #{job.id} status updated to {job.get_status_display()}.")
            
    return redirect('worker_dashboard')


@login_required
def service_job_history_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager', 'assistant_manager', 'finance']:
        return redirect('dashboard_router')
        
    archives = ServiceJobArchive.objects.all().order_by('-created_at')
    return render(request, 'services/dashboards/service_job_history.html', {
        'archives': archives
    })


@login_required
def marketer_analytics_view(request):
    request.user.refresh_from_db()
    allowed_roles = ['ceo', 'manager', 'general_manager', 'finance']
    if not request.user.is_superuser and getattr(request.user, 'role', None) not in allowed_roles:
        return redirect('dashboard_router')

    from decimal import Decimal
    marketers = User.objects.filter(role='marketer') if hasattr(User, 'role') else User.objects.none()

    marketer_stats_raw = []
    grand_total_revenue = Decimal('0.00')

    for marketer in marketers:
        referred_customers = User.objects.filter(referred_by=marketer) if hasattr(User, 'referred_by') else User.objects.none()
        
        total_spend = Decimal('0.00')
        for cust in referred_customers:
            cust_jobs = Job.objects.filter(customer=cust)
            for job in cust_jobs:
                if hasattr(job, 'quotation') and job.quotation and job.quotation.is_approved_by_client:
                    total_spend += job.quotation.total_amount or Decimal('0.00')

        grand_total_revenue += total_spend
        marketer_stats_raw.append({
            'marketer': marketer,
            'customer_count': referred_customers.count(),
            'total_spend': total_spend,
        })

    marketer_stats = []
    for item in marketer_stats_raw:
        spend = item['total_spend']
        percentage_share = (float(spend) / float(grand_total_revenue) * 100) if grand_total_revenue > 0 else 0.0
        estimated_commission = spend * Decimal('0.50')

        item['percentage_share'] = round(percentage_share, 1)
        item['estimated_commission'] = estimated_commission
        marketer_stats.append(item)

    referred_users = User.objects.filter(referred_by__isnull=False).select_related('referred_by').order_by('-date_joined') if hasattr(User, 'referred_by') else []

    return render(request, 'services/dashboards/marketer_analytics.html', {
        'marketer_stats': marketer_stats,
        'referred_users': referred_users,
    })


@login_required
def edit_site_config_view(request):
    """Allows CEO/Manager to edit About Us, Company Policy, Commission Percentage, and upload PDFs."""
    if not request.user.is_superuser and request.user.role not in ['ceo', 'manager', 'general_manager']:
        return redirect('dashboard_router')
        
    config = SiteConfiguration.get_solo()
    
    if request.method == 'POST':
        config.company_name = request.POST.get('company_name', config.company_name)
        config.contact_phone = request.POST.get('contact_phone', config.contact_phone)
        config.contact_email = request.POST.get('contact_email', config.contact_email)
        config.about_text = request.POST.get('about_text', '')
        config.policy_text = request.POST.get('policy_text', '')
        
        commission_val = request.POST.get('commission_percentage')
        if commission_val:
            config.commission_percentage = commission_val
        
        if 'about_pdf' in request.FILES:
            config.about_pdf = request.FILES['about_pdf']
        if 'policy_pdf' in request.FILES:
            config.policy_pdf = request.FILES['policy_pdf']
            
        config.save()
        return redirect('dashboard_router')
        
    return render(request, 'services/dashboards/edit_site_config.html', {'config': config})


@login_required
def marketer_dashboard_view(request):
    request.user.refresh_from_db()
    role = str(request.user.role).strip().lower() if request.user.role else ''
    if not request.user.is_superuser and role != 'marketer':
        return redirect('dashboard_router')
        
    referred_customers = User.objects.filter(referred_by=request.user)
    
    total_spend = 0
    customer_data = []
    for cust in referred_customers:
        cust_spend = 0
        customer_jobs = Job.objects.filter(customer=cust)
        for j in customer_jobs:
            if hasattr(j, 'quotation') and j.quotation and j.quotation.is_approved_by_client:
                cust_spend += float(j.quotation.total_amount)
        total_spend += cust_spend
        customer_data.append({
            'customer': cust,
            'total_spend': cust_spend
        })
        
    config = SiteConfiguration.get_solo()
    if request.user.commission_percentage is not None:
        commission_rate = float(request.user.commission_percentage)
    else:
        commission_rate = float(config.commission_percentage)
        
    estimated_commission = total_spend * (commission_rate / 100)
        
    context = {
        'referred_customers': referred_customers,
        'customer_data': customer_data,
        'total_spend': total_spend,
        'commission_rate': commission_rate,
        'estimated_commission': estimated_commission,
    }
    return render(request, 'services/dashboards/marketer_dashboard.html', context)


@login_required
def finance_part_payments_view(request):
    """
    Displays all jobs where quotations exist, tracking deposits paid, 
    remaining balances, timestamps, and live statuses with filters & export.
    """
    queryset = Job.objects.filter(quotation__isnull=False).select_related('customer', 'job_type', 'quotation')

    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    if search_query:
        queryset = queryset.filter(
            Q(id__icontains=search_query) | 
            Q(customer__username__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query)
        )

    export_format = request.GET.get('export', '')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="part_payments_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Job ID', 'Customer', 'Service Type', 'Job Status', 'Quoted Amount', 'Deposit Paid', 'Balance Remaining', 'Job Date'])
        
        for job in queryset:
            quote = getattr(job, 'quotation', None)
            writer.writerow([
                f"#{job.id}",
                job.customer.get_full_name() or job.customer.username,
                job.job_type.name if job.job_type else "N/A",
                job.get_status_display(),
                quote.total_amount if quote else 0.00,
                quote.deposit_amount if (quote and quote.is_deposit_paid) else 0.00,
                quote.balance_amount if quote else 0.00,
                job.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    context = {
        'jobs_list': queryset.order_by('-created_at'),
        'status_choices': Job.STATUS_CHOICES,
        'selected_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }
    return render(request, 'services/dashboards/finance_part_payments.html', context)


@login_required
def finance_invoices_view(request):
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
   
    jobs = Job.objects.all().select_related('customer', 'invoice').order_by('-id')

    for job in jobs:
        if job.status in ['settled', 'fully_paid'] and not hasattr(job, 'invoice'):
            invoice_num = f"INV-{job.id}-{random.randint(1000, 9999)}"
            Invoice.objects.get_or_create(
                job=job,
                defaults={'invoice_number': invoice_num}
            )

    all_statuses = Job.objects.values_list('status', flat=True).distinct()
    all_models = Job.objects.values_list('model_type', flat=True).distinct()

    status_filter = request.GET.get('status_filter', '')
    model_filter = request.GET.get('model_filter', '')

    if status_filter:
        jobs = jobs.filter(status=status_filter)
    if model_filter:
        jobs = jobs.filter(model_type=model_filter)

    if request.method == 'POST':
        if 'create_invoice' in request.POST:
            job_id = request.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            invoice_num = f"INV-{job.id}-{random.randint(1000, 9999)}"
            invoice_pdf_file = request.FILES.get('invoice_pdf')
           
            Invoice.objects.update_or_create(
                job=job,
                defaults={
                    'invoice_number': invoice_num,
                    'invoice_pdf': invoice_pdf_file
                }
            )
            job.status = 'settled'
            job.save()
            return redirect('finance_invoices')

    return render(request, 'services/dashboards/finance_invoices.html', {
        'jobs': jobs,
        'all_statuses': all_statuses,
        'all_models': all_models,
        'status_filter': status_filter,
        'model_filter': model_filter,
    })


@login_required
def download_invoice_pdf(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check permissions
    if not request.user.is_superuser and request.user.role not in ['ceo', 'finance', 'manager', 'general_manager', 'assistant_manager'] and job.customer != request.user:
        return redirect('dashboard_router')
   
    # Rule 1: Invoice should ONLY become accessible/generated when job status is marked as Completed
    # (Checking if status is completed, case-insensitive or exact match based on your system)
    job_status_lower = str(job.status).strip().lower()
    if job_status_lower not in ['completed', 'complete job', 'closed']:
        return HttpResponse("Invoice is not available yet. The job must be marked as completed first.", status=403)

    # Check if a pre-generated file exists, but skip if it's a PO job to ensure PO details display dynamically
    po_record = PurchaseOrderRecord.objects.filter(job=job).first()
    is_po_job = bool(po_record or getattr(job, 'is_po_job', False))

    if not is_po_job and hasattr(job, 'invoice') and job.invoice and job.invoice.invoice_pdf:
        return redirect(job.invoice.invoice_pdf.url)
   
    config = SiteConfiguration.get_solo()
    active_bank = CompanyBankAccount.objects.filter(is_active=True).first()
    inv = getattr(job, 'invoice', None)
    q = getattr(job, 'quotation', None)
    
    # Fetch dynamic item rows from invoice items first, fallback to quotation items if invoice items don't exist
    invoice_items = inv.items.all() if (inv and hasattr(inv, 'items') and inv.items.exists()) else (q.items.all() if (q and hasattr(q, 'items')) else [])
   
    items_html = ""
    if invoice_items:
        for item in invoice_items:
            line_total = item.get_total() if hasattr(item, 'get_total') else (item.quantity * item.amount)
            # Rule 2: Fixing Serial Number Display ("N/A") -> Pulling item or job serial number correctly
            item_serial = getattr(item, 'serial_number', None) or job.serial_number or 'N/A'
            items_html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 12px;">{item.description}</td>
                <td style="padding: 12px; text-align: center;">{item_serial}</td>
                <td style="padding: 12px; text-align: center;">{item.quantity}</td>
                <td style="padding: 12px; text-align: right;">₦{item.amount:,.2f}</td>
                <td style="padding: 12px; text-align: right;">₦{line_total:,.2f}</td>
            </tr>
            """
    else:
        fallback_amt = (inv.total_amount if inv and inv.total_amount else None) or (q.total_amount if q else 0.00)
        fallback_serial = job.serial_number or 'N/A'
        items_html = f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 12px;">{job.job_type.name if job.job_type else 'Repair Service'} - Completed Work</td>
            <td style="padding: 12px; text-align: center;">{fallback_serial}</td>
            <td style="padding: 12px; text-align: center;">1</td>
            <td style="padding: 12px; text-align: right;">₦{fallback_amt:,.2f}</td>
            <td style="padding: 12px; text-align: right;">₦{fallback_amt:,.2f}</td>
        </tr>
        """

    grand_total = (inv.total_amount if inv and inv.total_amount else None) or (q.total_amount if q else 0.00)

    # Rule 1 & 3: Conditional PO block - Only display for PO jobs with valid PO data
    po_details_html = ""
    if is_po_job and po_record:
        po_details_html = f"""
        <p style="margin: 3px 0;"><strong>PO Number:</strong> {po_record.po_number or 'N/A'}</p>
        <p style="margin: 3px 0;"><strong>Payment Terms:</strong> {po_record.payment_terms or 'Net 30 Days'}</p>
        <p style="margin: 3px 0;"><strong>PO Due Date:</strong> {po_record.due_date.strftime('%Y-%m-%d') if po_record.due_date else 'N/A'}</p>
        """

    html_content = f"""
    <html>
    <head><title>Invoice #{inv.invoice_number if inv else job.id} - {config.company_name}</title></head>
    <body style="font-family: Arial, sans-serif; padding: 40px; color: #333; max-width: 800px; margin: auto; border: 1px solid #ddd;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: #28a745; margin-bottom: 5px;">{config.company_name}</h1>
                <p style="margin: 0; color: #555;">Official Receipt / Invoice</p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0;"><strong>Address:</strong> {config.company_address or 'N/A'}</p>
                <p style="margin: 0;"><strong>Phone:</strong> {config.contact_phone or 'N/A'}</p>
                <p style="margin: 0;"><strong>Email:</strong> {config.contact_email or 'N/A'}</p>
            </div>
        </div>
        <hr style="border: 0; border-top: 2px solid #28a745; margin: 20px 0;">
        <table style="width: 100%; margin-bottom: 20px;">
            <tr>
                <td>
                    <p style="margin: 3px 0;"><strong>Billed To:</strong> {job.customer.first_name} {job.customer.last_name} (@{job.customer.username})</p>
                    <p style="margin: 3px 0;"><strong>Address:</strong> {job.customer.address or 'N/A'}, {job.customer.state or ''}</p>
                    {po_details_html}
                </td>
                <td style="text-align: right;">
                    <p style="margin: 3px 0;"><strong>Invoice Number:</strong> {inv.invoice_number if inv else f'INV-{job.id}'}</p>
                    <p style="margin: 3px 0;"><strong>Job Serial ID:</strong> #{job.id}</p>
                    <p style="margin: 3px 0;"><strong>Date:</strong> {job.created_at.strftime('%Y-%m-%d') if hasattr(job, 'created_at') else 'N/A'}</p>
                </td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
            <tr style="background-color: #181a1e; color: white;">
                <th style="padding: 10px; text-align: left;">Service Description</th>
                <th style="padding: 10px; text-align: center;">Serial Number</th>
                <th style="padding: 10px; text-align: center;">Qty</th>
                <th style="padding: 10px; text-align: right;">Unit Price</th>
                <th style="padding: 10px; text-align: right;">Total</th>
            </tr>
            {items_html}
        </table>
        <div style="float: right; width: 320px;">
            <p style="display: flex; justify-content: space-between; margin: 5px 0; font-size: 1.1em;"><span>Grand Total:</span> <strong style="color: #28a745;">₦{grand_total:,.2f}</strong></p>
            <p style="display: flex; justify-content: space-between; margin: 5px 0;"><span>Payment Status:</span> <strong style="color: #28a745;">FULLY PAID</strong></p>
        </div>
        <div style="clear: both; margin-top: 40px; background: #f9f9f9; padding: 15px; border-radius: 8px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">Status Confirmation</h4>
            <p style="margin: 0;">This serves as an official receipt that all balances for Job #{job.id} have been fully settled.</p>
        </div>

        <div style="margin-top: 20px; padding: 15px; background-color: #f9f9f9; border: 1px solid #eee; border-radius: 8px;">
            <h4 style="margin: 0 0 10px 0; color: #28a745;">Payment Information / Bank Details:</h4>
            <p style="margin: 3px 0;"><strong>Bank Name:</strong> {active_bank.bank_name if active_bank else 'No Active Bank Configured'}</p>
            <p style="margin: 3px 0;"><strong>Account Number:</strong> {active_bank.account_number if active_bank else 'N/A'}</p>
            <p style="margin: 3px 0;"><strong>Account Name:</strong> {active_bank.account_name if active_bank else 'N/A'}</p>
        </div>

        <p style="text-align:center; color:gray; margin-top: 40px; font-size: 0.9em;">Thank you for your business with {config.company_name}.</p>
    </body>
    </html>
    """
    return HttpResponse(html_content)

from datetime import datetime, date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Job, Quotation, PurchaseOrderRecord, StatementOfAccount, ServiceJobArchive, SiteConfiguration
from .forms import JobRequestForm

# --- PURCHASE ORDER (PO) & STATEMENT OF ACCOUNT WORKFLOW VIEWS ---
@login_required
def customer_submit_po_view(request, job_id):
    """
    Handles dedicated PO requests from the customer PO sidebar.
    Triggers only when explicitly invoked via the PO workflow route.
    """
    request.user.refresh_from_db()
    if request.user.role != 'customer' and not request.user.is_superuser:
        return redirect('dashboard_router')
        
    job = get_object_or_404(Job, id=job_id, customer=request.user)
    
    if request.method == 'POST':
        po_document = request.FILES.get('po_document')
        payment_terms = request.POST.get('payment_terms', 'Net 30')
        due_date = request.POST.get('due_date')
        
        if po_document:
            PurchaseOrderRecord.objects.update_or_create(
                job=job,
                defaults={
                    'customer': request.user,
                    'po_document': po_document,
                    'payment_terms': payment_terms,
                    'due_date': due_date if due_date else None,
                    'status': 'pending_finance_review'
                }
            )
            job.status = 'po_submitted'
            job.save()
            
            messages.success(request, "Purchase Order request submitted successfully via the PO portal!")
            return redirect('customer_job_detail', job_id=job.id)
        else:
            messages.error(request, "Please attach a valid PO document to proceed.")
            
    return redirect('customer_job_detail', job_id=job.id)

@login_required
def finance_po_list_view(request):
    """
    Dashboard view to review incoming customer PO requests.
    Restricted strictly to Finance, General Manager, CEO, and Superusers.
    Auto-syncs jobs and assigns any uploaded file/image as the PO document.
    """
    request.user.refresh_from_db()
    allowed_roles = ['finance', 'ceo', 'general_manager']
    if not request.user.is_superuser and request.user.role not in allowed_roles:
        return redirect('dashboard_router')
        
    corporate_jobs = Job.objects.filter(is_po_job=True)
    for job in corporate_jobs:
        po_record, created = PurchaseOrderRecord.objects.get_or_create(
            job=job,
            defaults={
                'customer': job.customer,
                'status': 'pending_finance_review',
                'payment_terms': 'Net 30'
            }
        )
        
        if not po_record.po_document:
            attached_file = None
            if hasattr(job, 'purchase_order') and job.purchase_order:
                attached_file = job.purchase_order
            elif hasattr(job, 'image1') and job.image1:
                attached_file = job.image1
            elif hasattr(job, 'image2') and job.image2:
                attached_file = job.image2
            elif hasattr(job, 'image3') and job.image3:
                attached_file = job.image3
            elif hasattr(job, 'quotation') and job.quotation and hasattr(job.quotation, 'document') and job.quotation.document:
                attached_file = job.quotation.document

            if attached_file:
                try:
                    po_record.po_document = attached_file
                    po_record.save()
                except Exception:
                    pass

    po_records = PurchaseOrderRecord.objects.select_related('job', 'job__customer').all().order_by('-created_at')
    
    return render(request, 'services/dashboards/finance_po_list.html', {
        'po_records': po_records,
    })

@login_required
def finance_approve_po_view(request, po_id):
    """
    Finance team / General Manager reviews and forwards the PO to the Executive/CEO dashboard.
    """
    request.user.refresh_from_db()
    allowed_roles = ['finance', 'general_manager']
    if not request.user.is_superuser and request.user.role not in allowed_roles:
        return redirect('dashboard_router')
        
    po_record = get_object_or_404(PurchaseOrderRecord, id=po_id)
    if request.method == 'POST':
        po_record.status = 'pending_executive_approval'
        po_record.save()
        messages.success(request, f"PO #{po_record.id} verified and forwarded to Executive/CEO for final approval.")
        
    return redirect('finance_po_list')


@login_required
def executive_approve_po_view(request, po_id):
    """
    Executive (CEO/GM) final approval view for Purchase Order requests.
    """
    request.user.refresh_from_db()
    allowed_roles = ['ceo', 'general_manager']
    if not request.user.is_superuser and request.user.role not in allowed_roles:
        return redirect('dashboard_router')
        
    po_record = get_object_or_404(PurchaseOrderRecord, id=po_id)
    if request.method == 'POST':
        po_record.status = 'approved'
        po_record.save()
        
        job = po_record.job
        if job:
            job.status = 'po_approved_pending_work'
            job.save()
            
        messages.success(request, f"PO #{po_record.id} fully approved and job unlocked for work execution!")
        
    return redirect('ceo_dashboard')


@login_required
def finance_upload_statement_view(request, job_id):
    """
    Finance uploads the Statement of Account upon job completion/delivery.
    """
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
        
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        statement_pdf = request.FILES.get('statement_pdf')
        notes = request.POST.get('notes', '')
        
        if statement_pdf:
            StatementOfAccount.objects.update_or_create(
                job=job,
                defaults={
                    'customer': job.customer,
                    'statement_pdf': statement_pdf,
                    'notes': notes,
                    'status': 'sent_to_customer'
                }
            )
            job.status = 'statement_sent'
            job.save()
            messages.success(request, f"Statement of Account generated & uploaded for Job #{job.id}.")
            
    return redirect('finance_invoices')


@login_required
def customer_approve_via_po(request, job_id):
    """
    Handles customer submission of dedicated manual PO details, payment terms, 
    custom due dates, and saves document upload so finance/CEO can view it instantly.
    """
    job = get_object_or_404(Job, id=job_id, customer=request.user)
    
    if request.method == 'POST':
        po_number = request.POST.get('po_number')
        payment_terms = request.POST.get('payment_terms', 'Net 30 Days')
        due_date_str = request.POST.get('due_date')
        po_document = request.FILES.get('po_document')
        
        parsed_due_date = None
        if due_date_str:
            try:
                parsed_due_date = datetime.strptime(due_date_str.strip(), '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Fallback format check if input sends dd/mm/yyyy
                    parsed_due_date = datetime.strptime(due_date_str.strip(), '%d/%m/%Y').date()
                except ValueError:
                    pass
                
        if not parsed_due_date:
            days_to_add = 30
            if '60' in payment_terms:
                days_to_add = 60
            elif '90' in payment_terms:
                days_to_add = 90
            elif 'immediate' in payment_terms.lower() or 'delivery' in payment_terms.lower():
                days_to_add = 0
            parsed_due_date = date.today() + timedelta(days=days_to_add)
        
        # Save PO status and data directly to Job model
        job.is_po_job = True
        if po_number:
            job.po_number = po_number
        job.save()
        
        # Approve quotation automatically upon PO submission
        quotation = getattr(job, 'quotation', None)
        if quotation:
            quotation.is_approved_by_client = True
            quotation.save()
        
        # Get or create the PurchaseOrderRecord and securely populate data
        po_record, created = PurchaseOrderRecord.objects.get_or_create(
            job=job,
            defaults={
                'customer': job.customer,
                'status': 'pending_finance_review',
                'po_number': po_number if po_number else f"PO-JOB-{job.id}",
                'payment_terms': payment_terms,
                'due_date': parsed_due_date,
                'po_document': po_document
            }
        )
        
        po_record.customer = job.customer
        if po_number:
            po_record.po_number = po_number
        if payment_terms:
            po_record.payment_terms = payment_terms
        if parsed_due_date:
            po_record.due_date = parsed_due_date
        if po_document:
            po_record.po_document = po_document
            
        po_record.status = 'pending_finance_review'
        po_record.save()
        
        job.status = 'pending_finance_review'
        job.save()
        
        messages.success(request, "Corporate Purchase Order submitted successfully for review!")
        return redirect('customer_job_detail', job_id=job.id)
        
    return redirect('customer_job_detail', job_id=job.id)

@login_required
def customer_confirm_po_payment_view(request, po_id):
    """
    Allows a customer to confirm or submit payment details for a purchase order.
    """
    po_record = get_object_or_404(PurchaseOrderRecord, id=po_id)
    
    if request.method == 'POST':
        po_record.status = 'payment_pending_confirmation'
        po_record.save()
        messages.success(request, "Payment confirmation submitted successfully to Finance.")
        return redirect('customer_jobs_list')
        
    return render(request, 'services/dashboards/customer_confirm_po.html', {
        'po_record': po_record
    })

@login_required
def finance_confirm_po_settlement_view(request, po_id):
    """
    Finance final clearance view: confirms payment, unlocks revenue, and archives job.
    """
    request.user.refresh_from_db()
    if not request.user.is_superuser and request.user.role != 'finance':
        return redirect('dashboard_router')
        
    po_record = get_object_or_404(PurchaseOrderRecord, id=po_id)
    if request.method == 'POST':
        po_record.status = 'settled'
        po_record.save()
        
        job = po_record.job
        job.status = 'settled'
        job.save()
        
        q = getattr(job, 'quotation', None)
        
        revenue_amount = q.total_amount if q else 0.00
        
        archive_entry, created = ServiceJobArchive.objects.get_or_create(
            job_id=job.id,
            defaults={
                'client_name': f"{job.customer.first_name} {job.customer.last_name} (@{job.customer.username})",
                'assigned_staff': job.assigned_worker.username if job.assigned_worker else "Unassigned",
                'job_description': job.description,
                'job_flow_status': "PO Settled",
                'total_amount': revenue_amount,
                'invoice_number': f"PO-INV-{job.id}",
                'has_quotation': bool(q),
                'job_day': job.created_at.strftime('%A'),
                'job_month': job.created_at.strftime('%B %Y'),
                'created_at': job.created_at
            }
        )
        
        if not created:
            archive_entry.total_amount = revenue_amount
            archive_entry.job_flow_status = "PO Settled"
            archive_entry.save()

        messages.success(request, f"PO #{po_record.id} fully settled and ₦{revenue_amount} cleared into company revenue.")
        
    return redirect('finance_po_list')
