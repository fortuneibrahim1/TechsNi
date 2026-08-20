from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        # List the name of the URL patterns you want to include
        return ['login']

    def location(self, item):
        return reverse(item)