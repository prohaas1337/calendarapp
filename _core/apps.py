from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '_core'

    def ready(self):
        import _core.signals  # Itt töltjük be a signalokat