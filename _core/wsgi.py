"""
WSGI config for _core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_core.settings')

application = get_wsgi_application()

# WhiteNoise beállítása a statikus fájlok kiszolgálásához
application = WhiteNoise(application, root=os.path.join(os.path.dirname(__file__), 'staticfiles'), prefix='static/')