"""
WSGI entrypoint for production.

Gunicorn command (used in Procfile and render.yaml):
    gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
             --workers 1 --bind 0.0.0.0:$PORT --timeout 120 wsgi:application
"""
from app import app, initialize_database

initialize_database(app)

# Gunicorn / gevent expect the WSGI callable to be named 'application'
application = app
