import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chiclane_project.settings')

# This is the line to change
application = get_wsgi_application()