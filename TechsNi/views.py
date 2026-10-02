from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from services.models import InstructionCatalog, CompanyInfo  # <--- Added CompanyInfo here!
from django.contrib.auth import get_user_model

User = get_user_model()


def custom_login_view(request):
    # Fetch all catalogs and company info
    catalogs = InstructionCatalog.objects.all().order_by('order')
    company_info = CompanyInfo.objects.all().first()  # <--- Fetch the company info

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
        'company_info': company_info,  # <--- Pass it into the context here!
    }
    return render(request, 'services/login.html', context)

@login_required
def portal_gateway_view(request):
    return render(request, 'store/portal_gateway.html')