from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'

class TonAppConfig(AppConfig):
    name = 'tasks' 

    def ready(self):
        # Ce code importe les signaux pour qu'ils soient enregistrés au démarrage de Django
        import tasks.signals