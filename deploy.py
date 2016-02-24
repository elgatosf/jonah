#!/usr/bin/env python
from __future__ import print_function

import os
import sys
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
from subprocess import call, check_output, CalledProcessError

import requests

working_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# environment names
general = 'general'
develop = 'develop'
staging = 'staging'
production = 'production'

# configuration names
NEW_RELIC_APP_NAME = 'NEW_RELIC_APP_NAME'
NEW_RELIC_API_KEY = 'NEW_RELIC_API_KEY'
DOCKER_IMAGE_NAME = 'DOCKER_IMAGE_NAME'
REDEPLOY_TRIGGER = 'REDEPLOY_TRIGGER'
ROOT_PASSWORD = 'ROOT_PASSWORD'
SECRET_KEY = 'SECRET_KEY'


class Deployer(object):
    def __init__(self, config_file_path = os.path.join(working_dir, 'deploy.ini')):
        self.parser = SafeConfigParser()
        self.parser.read(config_file_path)

    @staticmethod
    def __dir__():
        return ['build', 'develop', 'stop', 'reload', 'shell', 'tag', 'test', 'stage']

    @staticmethod
    def run(cmd, cwd=None):
        """Run a shell command"""
        try:
            if os.getenv("DEBUG", "False") == "True":
                print(cmd)
            return check_output(cmd.split(' '), cwd=working_dir if cwd is None else cwd)
        except CalledProcessError as e:
            print('Error\n\t' + e.output)
            exit(1)

    def get_configuration(self, configuration_name, environment='general'):
        try:
            return self.parser.get(environment, configuration_name)
        except (NoSectionError, NoOptionError):
            return self.parser.get('general', configuration_name)

    def get_container_id(self):
        """Returns the currently running container's ID if any"""
        container_id = self.run('docker ps -q --filter="ancestor=%s"' % (self.get_configuration('DOCKER_IMAGE_NAME', 'develop').replace('/', ':'))).split('\n')[0]
        return container_id

    def full_name(self, environment):
        # environment should be 'develop', 'staging', or 'production'
        return self.get_configuration('DOCKER_IMAGE_NAME', environment)

    def build(self, environment=develop):
        """Build the image"""
        self.stop()
        print("Building... ", end="")
        output = self.run('docker build -t %s %s' % (self.full_name(environment=environment), working_dir)).split('\n')
        num_steps = len(filter(lambda x: "Step" in x, output)) - 1
        num_cached = len(filter(lambda y: "cache" in y, output))
        print("OK, %i steps, %i cached" % (num_steps, num_cached))

    def stop(self):
        """Stop a previously running development server"""
        print("Stopping previously started containers... ", end="")
        image_name = self.get_configuration(DOCKER_IMAGE_NAME, develop).replace('/', ':')
        container_ids = self.run('docker ps -q --filter="ancestor=%s"' % image_name).split("\n")
        for container_id in container_ids:
            if len(container_id) > 0:
                print(container_id + ' ', end='')
                self.run('docker stop ' + container_id)
        print("OK")

    def develop(self):
        """Run dev server"""
        self.build(develop)
        print("Starting dev server... ", end="")
        output = self.run('docker run -d -p 80:80 --env DJANGO_PRODUCTION=false --env ROOT_PASSWORD='
                          + self.get_configuration(ROOT_PASSWORD, develop)
                          + ' --env SECRET_KEY=' + self.get_configuration(SECRET_KEY, develop)
                          + ' -v ' + working_dir+':/code ' + self.full_name(environment=develop))
        print("OK")

    def reload(self):
        """Reload Django process on dev server"""
        print("Reloading Django... ", end='')
        self.run('docker exec -t -i %s killall gunicorn' % self.get_container_id())
        print("OK")

    def shell(self):
        """Get a shell on the dev server"""
        cmd = 'docker exec -t -i %s /bin/bash' % self.get_container_id().split(' ')[0]
        call(cmd, shell=True)

    def tag(self, environment, tag=None):
        """Tag git version and docker version"""
        self.build()
        current_tag = self.run('git describe --tags').split('\n')[0]
        if tag:
            new_tag = tag
        else:
            new_tag = raw_input("Which tag should I use? (Current is %s, leave empty for 'latest'): " % current_tag)

        if len(new_tag) < 1 or new_tag == "\n":
            new_tag = 'latest'
        print("Tagging as '%s'... " % new_tag, end="")

        self.run('git tag -f ' + new_tag)
        self.run('docker tag -f %s:latest %s:%s' % (self.full_name(environment=develop), self.full_name(environment=environment), new_tag))
        print("OK")
        return new_tag

    def test(self):
        """Build and run Unit Tests"""
        self.build()
        # todo

    def push(self, environment):
        repo_name = self.get_configuration(DOCKER_IMAGE_NAME, environment)
        print("Pushing to '%s'... " % repo_name, end="")
        self.run('docker push ' + repo_name)
        print("OK")

    def notify_newrelic(self, environment):
        print("Notifying New Relic (%s)... " % environment, end="")
        sys.stdout.flush()
        post_headers = {
            'x-api-key': self.get_configuration(NEW_RELIC_API_KEY, environment)
        }
        post_data = {
            'deployment[app_name]': self.get_configuration(NEW_RELIC_APP_NAME, environment)
        }
        requests.post('https://api.newrelic.com/deployments.xml', data=post_data, headers=post_headers)

        print("OK")

    def notify_docker_cloud(self, environment):
        print("Notifying Docker Cloud to redeploy %s... " % environment, end="")
        sys.stdout.flush()
        requests.post(self.get_configuration(REDEPLOY_TRIGGER, environment))
        print("OK")

    def stage(self):
        """Deploy on test servers"""
        self.deploy(environment=staging)

    def deploy(self, environment=production):
        """Deploy on production servers"""
        tag = 'latest' if environment == staging else None
        tag = self.tag(environment, tag=tag)
        repo_name = self.get_configuration(DOCKER_IMAGE_NAME, environment)
        self.push(environment)
        self.notify_newrelic(environment)
        self.notify_docker_cloud('staging')

if __name__ == '__main__':
    d = Deployer()

    if len(sys.argv) > 1 and sys.argv[1] in dir(d):
        getattr(d, sys.argv[1])()
    else:
        print("USAGE:")
        print("\t%s %s\n" % (sys.argv[0], dir(d)))
        for arg in dir(d):
            print("\t" + arg + "\t" + getattr(d, arg).__doc__)
        exit(0)
