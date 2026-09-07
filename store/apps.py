from django.apps import AppConfig

class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'  # Change to your actual store app directory name if different

    def ready(self):
        import store.signals  # Ensures signals register on startup