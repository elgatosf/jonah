#!/usr/bin/env python
from __future__ import print_function

import os
import sys
from ConfigParser import SafeConfigParser
from subprocess import call, check_output, CalledProcessError

working_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Deployer(object):
    def __init__(self, config_file_path = os.path.join(working_dir, 'deploy.ini')):
        self.parser = SafeConfigParser()
        self.parser.read(config_file_path)

    @staticmethod
    def __dir__():
        return ['build', 'develop', 'stop', 'reload', 'shell', 'tag', 'test', 'stage', 'deploy']

    @staticmethod
    def run(cmd, cwd=None):
        try:
            print(cmd)
            return check_output(cmd.split(' '), cwd=working_dir if cwd is None else cwd)
        except CalledProcessError as e:
            print('Error\n\t' + e.output)
            exit(1)

    def get_container_id(self):
        """Returns the currently running container's ID if any"""
        container_id = self.run('docker ps -q --filter="ancestor=%s:%s"' % (self.parser.get('develop', 'REPOSITORY_NAME'), self.parser.get('general', 'DOCKER_IMAGE_NAME'))).split('\n')[0]
        return container_id

    def full_name(self, environment='develop'):
        # environment should be 'develop', 'staging', or 'production'
        return "%s/%s" % (self.parser.get(environment, 'REPOSITORY_NAME'), self.parser.get('general', 'DOCKER_IMAGE_NAME'))

    def build(self, environment='develop'):
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
        container_ids = self.run('docker ps -q --filter="ancestor=%s:%s"' % (self.parser.get('develop', 'REPOSITORY_NAME'), self.parser.get('general', 'DOCKER_IMAGE_NAME'))).split("\n")
        for container_id in container_ids:
            if len(container_id) > 0:
                print(container_id + ' ', end='')
                self.run('docker stop ' + container_id)
        print("OK")

    def develop(self):
        """Run dev server"""
        self.build()
        print("Starting dev server... ", end="")
        output = self.run('docker run -d -p 80:80 --env DJANGO_PRODUCTION=false --env ROOT_PASSWORD=' + self.parser.get('general', 'ROOT_PASSWORD') + ' --env SECRET_KEY=' + self.parser.get('production', 'SECRET_KEY') + ' -v ' + working_dir+':/code ' + self.full_name(environment='develop'))
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

    def tag(self):
        """Tag git version and docker version"""
        self.build()
        print("Tagging...")
        current_tag = self.run('git describe --tags').split('\n')[0]
        new_tag = raw_input("Which tag should I use? (Current is %s, leave empty for staging tag): " % current_tag)

        if len(new_tag) < 1:
            new_tag = 'staging'
        self.run('git tag -f ' + new_tag)
        self.run('docker tag -f %s:latest %s:%s' % (self.full_name(environment='develop'), self.full_name(environment='staging'), new_tag))

    def test(self):
        """Build and run Unit Tests"""
        self.build()
        # todo

    def stage(self):
        """Deploy on test servers"""
        self.build()
        self.tag()
        # todo
        # docker push ***REMOVED***/***REMOVED***/***REMOVED***:latest
        # tell newrelic a deployment is happening
        # tell tutum to reload/redeploy

    def deploy(self):
        """Deploy on production servers"""
        self.build()
        # todo
        # tag?
        # docker push
        # tell newrelic a deployment is happening
        # tell tutum to reload/redeploy

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
