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
    psmisc \
    libxml2-dev \
    libxslt1-dev \
    ipython

RUN easy_install pip
RUN apt-get build-dep -y python-psycopg2

# Add non-privileged user for processes that don't want to run as root
RUN adduser --disabled-password --gecos '' r

# Handle urllib3 InsecurePlatformWarning
RUN apt-get install -y libffi-dev libssl-dev libpython2.7-dev

# Install Python Requirements
ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt --ignore-installed

# Install System Requirements
ADD jonah/apt-packages.txt /aptpackages.txt
RUN apt-get install -y $(grep -vE "^\s*#" /aptpackages.txt  | tr "\n" " ")

# Run special system commands
ADD jonah/finalize_build.sh /systeminitialization.sh
RUN chmod ug+x /systeminitialization.sh
RUN /systeminitialization.sh

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
ADD jonah /jonah
RUN ln -s /jonah/nginx.conf /etc/nginx/sites-enabled/django_docker.conf
RUN rm /etc/nginx/sites-enabled/default

# Enable production settings by default; for development, this can be set to
# `false` in `docker run --env`
ENV DJANGO_PRODUCTION=true
ENV NEW_RELIC_LICENSE_KEY=invalid
ENV NEW_RELIC_APP_NAME=Developer
ENV DJANGO_SETTINGS_MODULE=ddp.settings
ENV NEW_RELIC_CONFIG_FILE=/jonah/newrelic.ini
ENV NEW_RELIC_ENVIRONMENT=development
ENV TERM xterm

# Configure Django project
ADD . /code
WORKDIR /code
RUN chmod ug+x /code/jonah/spinup.sh

# Configure Supervisor
ADD jonah/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Run Supervisor
CMD ["/usr/bin/supervisord"]
