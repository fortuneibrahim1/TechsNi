from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from services.models import InstructionCatalog  # Adjust import if your model lives elsewhere
from django.contrib.auth import get_user_model
import qrcode
import base64
from io import BytesIO

User = get_user_model()


def custom_login_view(request):
    # Fetch all catalogs ordered by their display number so they render on the root login page
    catalogs = InstructionCatalog.objects.all().order_by('order')

    if request.method == 'POST':
        # Use Django's AuthenticationForm to validate the POST data
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Explicitly force redirect to your portal gateway after login
            return redirect('portal_gateway')
    else:
        form = AuthenticationForm()
        
    # Generate the QR code dynamically for the portal
    portal_url = request.build_absolute_uri('/')
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(portal_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'form': form,
        'catalogs': catalogs,
        'qr_code': qr_code_base64,
    }
    return render(request, 'services/login.html', context)


@login_required
def portal_gateway_view(request):
    return render(request, 'store/portal_gateway.html')