# chiclane_project/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

# Set the settings module for the 'wsgi' application.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chiclane_project.settings')

# This is the crucial line Vercel is looking for.
# It gets the Django WSGI application and assigns it to the variable 'app'.
app = get_wsgi_application()