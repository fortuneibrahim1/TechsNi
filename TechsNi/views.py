from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from services.models import InstructionCatalog  # Adjust import if your model lives elsewhere

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
        
    context = {
        'form': form,
        'catalogs': catalogs,
    }
    return render(request, 'services/login.html', context)
@login_required
def portal_gateway_view(request):
    return render(request, 'store/portal_gateway.html')