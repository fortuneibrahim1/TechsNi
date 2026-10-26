from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from services.models import InstructionCatalog  # Adjust import if your model lives elsewhere
from django.contrib.auth import get_user_model

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
        
    context = {
        'form': form,
        'catalogs': catalogs,
    }
    return render(request, 'services/login.html', context)

from services.models import GameConfiguration
from services.models import UserGameReward  # or whichever app holds UserGameReward

@login_required
def portal_gateway_view(request):
    try:
        config = GameConfiguration.get_solo()
    except Exception:
        config = None

    try:
        user_reward = UserGameReward.objects.filter(user=request.user).first()
    except Exception:
        user_reward = None

    has_played = user_reward is not None

    context = {
        'config': config,
        'user_reward': user_reward,
        'has_played': has_played,
    }
    return render(request, 'store/portal_gateway.html', context)