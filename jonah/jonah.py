#!/usr/bin/python
from __future__ import print_function

import os
import sys
import subprocess
import shlex
import shutil

# requests might now be available. Don't run the "deploy" command in this case
try:
    import requests
except ImportError:
    pass

if sys.version_info >= (3, 0):
    from configparser import ConfigParser, NoSectionError, NoOptionError
else:
    from ConfigParser import SafeConfigParser as ConfigParser, NoSectionError, NoOptionError

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
    debug_mode = False
    already_built = False

    def __init__(self, config_file_path=os.path.join(os.getcwd(), 'jonah.ini')):
        self.parser = ConfigParser()
        self.parser.read(config_file_path)
        self.working_dir = os.getcwd()

    @staticmethod
    def __dir__():
        return ['initialize', 'build', 'cleanbuild', 'develop', 'compilemessages', 'stop', 'reload', 'shell', 'tag',
                'test', 'stage', 'deploy', 'direct_deploy', 'clean']

    def run(self, cmd, cwd=None, exceptions_should_bubble_up=False, spew=False):
        """Run a shell command"""
        if self.debug_mode:
            print('\n> ' + cmd)

        if spew:
            # return live output for the function to handle instead of one blob
            return subprocess.Popen(shlex.split(cmd), cwd=self.working_dir if cwd is None else cwd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)

        try:
            return subprocess.check_output(shlex.split(cmd), cwd=self.working_dir if cwd is None else cwd,
                                           stderr=subprocess.STDOUT,).decode('utf-8')
        except subprocess.CalledProcessError as e:
            if exceptions_should_bubble_up:
                raise
            else:
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
        docker_image_name = self.get_configuration('DOCKER_IMAGE_NAME', 'develop')
        container_id = self.run('docker ps -q --filter=ancestor=%s' % docker_image_name).split('\n')[0]
        return container_id

    def full_name(self, environment):
        # environment should be 'develop', 'staging', or 'production'
        return self.get_configuration('DOCKER_IMAGE_NAME', environment)

    def backspace(self, string_to_escape):
        if string_to_escape is None:
            return
        for char in string_to_escape:
            print('\b', end='')
        print('\b', end='')

    # User Actions #####################################################################################################

    def initialize(self):
        """Initialize a new jonah project in the current directory"""

        if len(sys.argv) > 2 and sys.argv[2] != 'debug':
            project_name = sys.argv[2]
        else:
            q = 'Please enter a name for your new project: '
            if sys.version_info >= (3, 0):
                project_name = input(q)
            else:
                project_name = raw_input(q)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        support_files_dir = os.path.join(base_dir, 'support_files')

        self.printout('Creating \'{}\' directory... '.format(project_name), False)
        # In Python 3 there is exception FileExistsError. But it is not available
        # in Python 2. For Python 2 fall back to OSError exception.
        if sys.version_info < (3, 0):
            FileExistsError = OSError
        else:
            from builtins import FileExistsError
        try:
            shutil.copytree(support_files_dir, os.path.join(self.working_dir, project_name))
        except (OSError, FileExistsError):
            print('A directory called "{}" already exists. Please choose another directory name.'.format(project_name))
            return
        self.printout('OK')

        old_cwd = self.working_dir
        os.chdir(os.path.join(self.working_dir, project_name))
        self.working_dir = os.getcwd()
        self.parser.read(os.path.join(self.working_dir, 'jonah.ini'))

        self.build()
        self.printout("Creating 'ddp' project... ", False)
        output = self.run('docker run --env DJANGO_SETTINGS_MODULE= -v ' + self.working_dir + ':/code '
                          + self.full_name(environment=develop)
                          + ' django-admin.py startproject ddp')
        self.printout(output, False)
        if len(output) < 1:
            self.printout("OK")

        self.working_dir = os.getcwd()
        os.chdir(old_cwd)

    def build(self, environment=develop, clean=False):
        """Build the image"""
        if self.already_built:
            return

        self.stop()
        self.printout("Building ", False)
        run_command = 'docker build -t %s %s'
        if clean:
            run_command += ' --no-cache'
        proc = self.run(run_command % (self.full_name(environment=environment), self.working_dir), spew=True)

        step_count = None
        line = None
        lastline = None
        while True:
            lastline = line
            line = proc.stdout.readline().decode('utf-8')
            if len(line) < 1:
                break
            if 'Step ' in line:
                self.backspace(step_count)
                step_count = line.split(' : ')[0]
                print('o ' + step_count, end='')
                continue
            if 'Using cache' in line:
                self.backspace(step_count + ' ')
                print('c ' + step_count, end='')

        proc.wait()
        if proc.returncode == 0:
            print(' OK')
        else:
            print("\nBuild failed with '{}'".format(lastline.strip()))
        self.already_built = True

    def cleanbuild(self, environment=develop):
        """Build the image from scratch"""
        self.build(environment=environment, clean=True)

    def stop(self):
        """Stop a previously running development server"""
        self.printout("Stopping previously started containers... ", False)
        image_name = self.get_configuration(DOCKER_IMAGE_NAME, develop)
        container_ids = self.run('docker ps -q --filter=ancestor=%s' % image_name).split('\n')
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
                          + ' -v ' + self.working_dir+':/code ' + self.full_name(environment=develop))
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
        subprocess.call(cmd, shell=True)

    def tag(self, environment, tag=None):
        """Tag git version and docker version"""
        self.build()
        if tag:
            new_tag = tag
        else:
            try:
                current_tag = self.run('git describe --tags', exceptions_should_bubble_up=True).split('\n')[0]
            except subprocess.CalledProcessError:
                current_tag = 'latest'
            q = "Which tag should I  use? (Current is %s, leave empty for 'latest'): " % current_tag
            if sys.version_info >= (3, 0):
                new_tag = input(q)
            else:
                new_tag = raw_input(q)
        if len(new_tag) < 1 or new_tag == "\n":
            new_tag = 'latest'
        self.printout("Tagging as '%s'... " % new_tag, False)

        self.run('git tag -f ' + new_tag)
        self.run('docker tag %s:latest %s:%s' % (self.full_name(environment=develop), self.full_name(environment=environment), new_tag))
        self.printout("OK")
        return new_tag

    def compilemessages(self):
        """Compile I18N Strings"""
        container_id = self.get_container_id()

        self.printout("Running compilemessages... ", False)
        cmd = ''
        if len(container_id) >= 1:
            container_id = self.get_container_id()
            cmd = 'docker exec -t -i %s python /code/ddp/manage.py compilemessages' % container_id.split(' ')[0]
        else:
            cmd = 'docker run --env DJANGO_PRODUCTION=false --env SECRET_KEY=not_so_secret' \
                  + ' -v ' + self.working_dir + ':/code ' \
                  + '-w=/code/ddp/ ' + self.full_name(environment=develop) \
                  + ' python /code/ddp/manage.py compilemessages'
        try:
            output = self.run(cmd, exceptions_should_bubble_up=True).split("\n")
            self.printout(output)
        except subprocess.CalledProcessError as e:
            self.printout("No messages found")

    def test(self):
        """Build and run Unit Tests"""
        self.build()
        self.compilemessages()
        print('Beginning Unit Tests...')
        proc = self.run('docker run --env DJANGO_PRODUCTION=false --env SECRET_KEY=not_so_secret'
                        + ' -v ' + self.working_dir + ':/code '
                        + '-v=' + self.working_dir + '/artifacts:/artifacts '
                        + '-w=/code/ '
                        + self.full_name(environment=develop)
                        + ' ./test.sh',
                        spew=True)
        while True:
            char = proc.stdout.read(1)
            if len(char) < 1:
                break
            print(char, end='')

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

    def direct_deploy(self, environment=production):
        """Deploy as tag master on production server, without warning. Danger Zone."""
        self.build()
        self.tag(environment, tag=environment)
        self.push(environment)
        self.notify_newrelic(environment)

    def deploy(self, environment=production):
        """Deploy on production servers"""
        self.test()
        tag = 'latest' if environment == staging else None
        self.tag(environment, tag=tag)
        self.direct_deploy(environment=environment)

    def clean(self):
        """Delete exited containers, dangling images, and volumes"""
        self.printout("Deleting exited containers... ", False)
        exited_containers = self.run("docker ps -a -q -f status=exited").split("\n")
        for exited_container in exited_containers:
            if len(exited_container) > 0:
                self.printout(exited_container + ' ', False)
                self.run("docker rm -v %s" % exited_container)
        self.printout("OK")

        self.printout("Deleting dangling images... ", False)
        dangling_images = self.run('docker images -f "dangling=true" -q').split("\n")
        dangling_images.reverse()
        for dangling_image in dangling_images:
            if len(dangling_image) > 0:
                self.printout(dangling_image + ' ', False)
                self.run("docker rmi -f %s" % dangling_image)
        self.printout("OK")

        self.printout("Deleting unused volumes... ", False)
        dangling_volumes = self.run('docker volume ls -qf dangling=true').split("\n")
        for dangling_volume in dangling_volumes:
            if len(dangling_volume) > 0:
                self.printout(dangling_volume + ' ', False)
                self.run("docker volume rm %s" % dangling_volume)
        self.printout("OK")


if __name__ == '__main__':
    d = Deployer()

    if len(sys.argv) > 1 and sys.argv[1] in dir(d):
        if len(sys.argv) > 2 and sys.argv[2] == 'debug':
            d.debug_mode = True
        getattr(d, sys.argv[1])()
    else:
        print("USAGE:")
        print("\t%s <COMMAND>, where command is one of the following:\n" % sys.argv[0])

        for arg in dir(d):
            print("\t" + arg.ljust(10) + "\t" + getattr(d, arg).__doc__)
        exit(0)
