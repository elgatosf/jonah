#!/usr/bin/env python
from __future__ import print_function

import os
import sys
from subprocess import call, check_output, CalledProcessError

working_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class Deployer(object):
    image_name = 'fizz'
    repository_name = {
        'develop': '***REMOVED***',
        'stage': '***REMOVED***/***REMOVED***/***REMOVED***',
        'live': 'omsn',
    }

    configuration = {
        'root_password': '123123',
        'secret_key': 'abcba',
    }

    def __init__(self):
        # todo: init with config
        pass

    @staticmethod
    def __dir__():
        return ['build', 'develop', 'stop', 'reload', 'shell', 'tag', 'test', 'stage', 'deploy']

    @staticmethod
    def run(cmd):
        try:
            return check_output(cmd.split(' '))
        except CalledProcessError as e:
            print('Error\n\t' + e.output)
            exit(1)

    def get_container_id(self):
        """Returns the currently running container's ID if any"""
        container_id = self.run('docker ps -q --filter="ancestor=%s:%s"' % (self.repository_name['develop'], self.image_name)).split('\n')[0]
        return container_id

    def full_name(self, environment='develop'):
        # environment should be 'develop', 'stage', or 'live'
        return "%s:%s" % (self.repository_name[environment], self.image_name)

    def build(self, environment='develop'):
        """Build the image"""
        print("Building... ", end="")
        output = self.run('docker build -t %s %s' % (self.full_name(environment=environment), working_dir))
        print("OK")

    def stop(self):
        """Stop a previously running development server"""
        print("Stopping previously started containers... ", end="")
        container_ids = self.run('docker ps -q --filter="ancestor=%s:%s"' % (self.repository_name['develop'], self.image_name)).split("\n")
        for container_id in container_ids:
            if len(container_id) > 0:
                print(container_id + ' ', end='')
                self.run('docker stop ' + container_id)
        print("OK")

    def develop(self):
        """Run dev server"""
        self.build()
        self.stop()
        print("Starting dev server... ", end="")
        output = self.run('docker run -d -p 80:80 --env DJANGO_PRODUCTION=false --env ROOT_PASSWORD=' + self.configuration['root_password'] + ' --env SECRET_KEY=' + self.configuration['secret_key'] + ' -v ' + working_dir+':/code ' + self.full_name(environment='develop'))
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
        # todo
        # git tag
        # docker tag -f ***REMOVED***/fizz:latest ***REMOVED***/***REMOVED***/***REMOVED***:latest

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
        """Deploy on live servers"""
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
