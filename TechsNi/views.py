import base64
from io import BytesIO
import qrcode
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from services.models import InstructionCatalog, CompanyInfo
from django.contrib.auth import get_user_model

User = get_user_model()


def custom_login_view(request):
    # Fetch catalogs and company info for the announcement banner
    catalogs = InstructionCatalog.objects.all().order_by('order')
    company_info = CompanyInfo.objects.all().first()

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

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('portal_gateway')
    else:
        form = AuthenticationForm()
        
    context = {
        'form': form,
        'catalogs': catalogs,
        'company_info': company_info,
        'portal_url': portal_url,
        'qr_code_image': qr_base64,
    }
    return render(request, 'services/login.html', context)

@login_required
def portal_gateway_view(request):
    return render(request, 'store/portal_gateway.html')