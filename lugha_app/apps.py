from django.apps import AppConfig


class LughaAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lugha_app'

    def ready(self):
        import lugha_app.signals
