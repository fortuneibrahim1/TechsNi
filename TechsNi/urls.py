from django.contrib import admin
from django.urls import path, include, reverse
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import Sitemap
from TechsNi.views import portal_gateway_view, custom_login_view

# Define the sitemap class for your static/login pages
class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return ['login']  # Points to your login page's url name

    def location(self, item):
        return reverse(item)

# Dictionary of sitemaps to pass to the sitemap view
sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # The main URL now opens your Login page first!
    path('', custom_login_view, name='login'),
    
    # The portal gateway lives here after login
    path('gateway/', portal_gateway_view, name='portal_gateway'),
    
    path('services/', include('services.urls')),
    path('store/', include('store.urls')),

    # Sitemap route
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)