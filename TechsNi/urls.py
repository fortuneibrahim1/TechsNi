from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from TechsNi.views import portal_gateway_view, custom_login_view

def sitemap_view(request):
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://techsni.com.ng/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>'''
    return HttpResponse(xml_content, content_type="application/xml")

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # The main URL now opens your Login page first!
    path('', custom_login_view, name='login'),
    
    # The portal gateway lives here after login
    path('gateway/', portal_gateway_view, name='portal_gateway'),
    
    path('services/', include('services.urls')),
    path('store/', include('store.urls')),

    # Sitemap route
    path('sitemap.xml', sitemap_view, name='sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)