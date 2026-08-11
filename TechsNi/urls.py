from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from TechsNi.views import portal_gateway_view, custom_login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # The main URL now opens your Login page first!
    path('', custom_login_view, name='login'),
    
    # The portal gateway lives here after login
    path('gateway/', portal_gateway_view, name='portal_gateway'),
    
    path('services/', include('services.urls')),
    path('store/', include('store.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)