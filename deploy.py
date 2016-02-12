#!/usr/bin/env python
from __future__ import print_function
from subprocess import check_output

import sys


class Deployer(object):
    image_name = 'fizz'
    repository_name = {
        'develop': '***REMOVED***',
        'stage': '***REMOVED***/***REMOVED***/***REMOVED***',
        'live': 'omsn',
    }

    def __init__(self):
        # todo: init with config
        pass

    @staticmethod
    def __dir__():
        return ['build', 'develop', 'tag', 'test', 'stage', 'deploy']

    def full_name(self, environment='develop'):
        # environemnt should be 'develop', 'stage', or 'live'
        return "%s:%s" % (self.repository_name[environment], self.image_name)

    def build(self, environment='develop'):
        """Build the image"""
        print("Building... ", end="")
        output = check_output(['docker', 'build', '-t', self.full_name(environment=environment), '.'])
        print("OK")

    def develop(self):
        """Run dev server"""
        self.build()
        # todo
        # docker run -d -p 80:80 --env DJANGO_PRODUCTION=false --env ROOT_PASSWORD=123123
        # --env SECRET_KEY=abcabcabca -v (pwd):/code ***REMOVED***/fizz

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
