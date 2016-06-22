#!/usr/bin/python
from __future__ import print_function

import os
import sys

if sys.version_info >= (3, 0):
    from configparser import SafeConfigParser, NoSectionError, NoOptionError
else:
    from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

from subprocess import call, check_output, CalledProcessError
if sys.version_info >= (3, 0):
    from subprocess import getoutput

# requests might now be available. Don't run the "deploy" command in this case
try:
    import requests
except ImportError:
    pass

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
        return ['build', 'develop', 'stop', 'reload', 'shell', 'tag', 'test', 'stage', 'deploy']

    @staticmethod
    def run(cmd, cwd=None):
        """Run a shell command"""
        try:
            if os.getenv("DEBUG", "False") == "True":
                print(cmd)
            if sys.version_info >= (3, 0):
                return getoutput(cmd)
            else:
                return check_output(cmd.split(' '), cwd=working_dir if cwd is None else cwd)
        except CalledProcessError as e:
            print('Error\n\t' + e.output)
            exit(1)

    @staticmethod
    def printout(text, add_newline=True):
        if sys.version_info >= (3, 0):
            print(text, end="\n" if add_newline else "", flush=True)
        else:
            print(text, end="\n" if add_newline else "")

    def get_configuration(self, configuration_name, environment='general'):
        try:
            return self.parser.get(environment, configuration_name)
        except (NoSectionError, NoOptionError):
            return self.parser.get('general', configuration_name)

    def get_container_id(self):
        """Returns the currently running container's ID if any"""
        container_id = self.run('docker ps -q --filter="ancestor=%s"' % (self.get_configuration('DOCKER_IMAGE_NAME', 'develop'))).split('\n')[0]
        return container_id

    def full_name(self, environment):
        # environment should be 'develop', 'staging', or 'production'
        return self.get_configuration('DOCKER_IMAGE_NAME', environment)

    def build(self, environment=develop):
        """Build the image"""
        self.stop()
        self.printout("Building... ", False)
        output = self.run('docker build -t %s %s' % (self.full_name(environment=environment), working_dir)).split('\n')
        num_steps = len(list(filter(lambda x: "Step" in x, output))) - 1
        num_cached = len(list(filter(lambda y: "cache" in y, output)))
        self.printout("OK, %i steps, %i cached" % (num_steps, num_cached))

    def stop(self):
        """Stop a previously running development server"""
        self.printout("Stopping previously started containers... ", False)
        image_name = self.get_configuration(DOCKER_IMAGE_NAME, develop)
        container_ids = self.run('docker ps -q --filter="ancestor=%s"' % image_name).split("\n")
        for container_id in container_ids:
            if len(container_id) > 0:
                self.printout(container_id + ' ', False)
                self.run('docker stop ' + container_id)
        self.printout("OK")

    def develop(self):
        """Run dev server"""
        self.build(develop)
        self.printout("Starting dev server... ", False)
        output = self.run('docker run -d -p 80:80 --env DJANGO_PRODUCTION=false --env ROOT_PASSWORD='
                          + self.get_configuration(ROOT_PASSWORD, develop)
                          + ' --env SECRET_KEY=' + self.get_configuration(SECRET_KEY, develop)
                          + ' -v ' + working_dir+':/code ' + self.full_name(environment=develop))
        self.printout("OK")

    def reload(self):
        """Reload Django process on dev server"""
        self.printout("Reloading Django... ", False)
        self.run('docker exec -t -i %s killall gunicorn' % self.get_container_id())
        self.printout("OK")

    def shell(self):
        """Get a shell on the dev server"""
        container_id = self.get_container_id()
        if len(container_id) < 1:
            self.develop()
            container_id = self.get_container_id()
        cmd = 'docker exec -t -i %s /bin/bash' % container_id.split(' ')[0]
        call(cmd, shell=True)

    def tag(self, environment, tag=None):
        """Tag git version and docker version"""
        self.build()
        current_tag = self.run('git describe --tags').split('\n')[0]
        if tag:
            new_tag = tag
        else:
            if sys.version_info >= (3, 0):
                new_tag = input("Which tag should I use? (Current is %s, leave empty for 'latest'): " % current_tag)
            else:
                new_tag = raw_input("Which tag should I use? (Current is %s, leave empty for 'latest'): " % current_tag)

        if len(new_tag) < 1 or new_tag == "\n":
            new_tag = 'latest'
        self.printout("Tagging as '%s'... " % new_tag, False)

        self.run('git tag -f ' + new_tag)
        self.run('docker tag %s:latest %s:%s' % (self.full_name(environment=develop), self.full_name(environment=environment), new_tag))
        self.printout("OK")
        return new_tag

    def test(self):
        """Build and run Unit Tests"""
        self.build()
        print("Running Tests... ", end="")
        output = self.run('docker run --env DJANGO_PRODUCTION=false --env SECRET_KEY=not_so_secret'
            + ' -w="/code/ddp/" '
            + self.full_name(environment=develop)
            + ' ./test.sh')
        print(output)

    def push(self, environment):
        repo_name = self.get_configuration(DOCKER_IMAGE_NAME, environment)
        self.printout("Pushing to '%s'... " % repo_name, False)
        self.run('docker push ' + repo_name)
        self.printout("OK")

    def notify_newrelic(self, environment):
        self.printout("Notifying New Relic (%s)... " % environment, False)
        sys.stdout.flush()
        post_headers = {
            'x-api-key': self.get_configuration(NEW_RELIC_API_KEY, environment)
        }
        post_data = {
            'deployment[app_name]': self.get_configuration(NEW_RELIC_APP_NAME, environment)
        }
        requests.post('https://api.newrelic.com/deployments.xml', data=post_data, headers=post_headers)

        self.printout("OK")

    def notify_docker_cloud(self, environment):
        self.printout("Notifying Docker Cloud to redeploy %s... " % environment, False)
        sys.stdout.flush()
        requests.post(self.get_configuration(REDEPLOY_TRIGGER, environment))
        self.printout("OK")

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
