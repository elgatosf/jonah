FROM ubuntu:14.04.4

# Set terminal to be noninteractive
ENV DEBIAN_FRONTEND noninteractive

# Install packages
RUN apt-get update && apt-get install -y \
    git \
    nginx \
    python-dev \
    python-setuptools \
    python-urllib3 \
    supervisor \
    vim \
    psmisc
RUN easy_install pip
RUN apt-get build-dep -y python-psycopg2

# Add non-privileged user for processes that don't want to run as root
RUN adduser --disabled-password --gecos '' r

# Handle urllib3 InsecurePlatformWarning
RUN apt-get install -y libffi-dev libssl-dev libpython2.7-dev
RUN pip install requests[security] ndg-httpsclient pyasn1 newrelic gunicorn

# Install Python Requirements
ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# configure environment
RUN mkdir /djangomedia
RUN mkdir /static
RUN mkdir /logs
RUN mkdir /logs/nginx
RUN mkdir /logs/gunicorn

# Expose ports
# 80 = Nginx
# 8000 = Gunicorn
EXPOSE 80 8000

# Configure Nginx
ADD deployment /deployment
RUN ln -s /deployment/nginx.conf /etc/nginx/sites-enabled/django_docker.conf
RUN rm /etc/nginx/sites-enabled/default

# Enable production settings by default; for development, this can be set to
# `false` in `docker run --env`
ENV DJANGO_PRODUCTION=true
ENV NEW_RELIC_LICENSE_KEY=invalid
ENV NEW_RELIC_APP_NAME=Developer
ENV NEW_RELIC_CONFIG_FILE=/deployment/newrelic.ini
ENV NEW_RELIC_ENVIRONMENT=development

# Configure Django project
ADD . /code
WORKDIR /code
RUN chmod ug+x /code/deployment/initialize.sh

# Configure Supervisor
RUN touch /code/supervisord_local.conf
RUN cat /code/deployment/supervisord.conf /code/supervisord_local.conf > /etc/supervisor/conf.d/supervisord.conf

# Run Supervisor
CMD ["/usr/bin/supervisord"]
