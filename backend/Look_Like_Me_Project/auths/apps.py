from django.apps import AppConfig

class AuthsConfig(AppConfig):
    name = 'auths'

    def ready(self):
        import auths.signals
