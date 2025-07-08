from django.apps import AppConfig

class ContractsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.contracts'
    verbose_name = 'Contract Management'

    def ready(self):
        pass