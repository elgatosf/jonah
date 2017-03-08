#!/bin/bash
# This script initializes the Django project. It will be executed (from 
# supervisord) every time the Docker image is run.

cd /code/ddp/

# Initialize Django project
python /code/ddp/manage.py collectstatic --noinput --clear
python /code/ddp/manage.py migrate --noinput

# (re)compile Translations
python /code/ddp/manage.py compilemessages || echo "Did not find messages to compile (or other error occurred)"
