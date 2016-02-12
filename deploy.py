import sys


class Deployer(object):

    local_repository_name = '***REMOVED***'
    local_image_name = 'fizz'
    testing_repository_name = '***REMOVED***/***REMOVED***/***REMOVED***'

    def __init__(self):
        # todo: init with config
        pass


    def __dir__(self):
        return ['build', 'develop', 'tag', 'test', 'stage', 'deploy']


    def build(self):
        """Build the image"""
        # todo
        # docker build -t ***REMOVED***/fizz .
        pass


    def develop(self):
        """Run dev server"""
        build()
        # todo
        # docker run -d -p 80:80 --env DJANGO_PRODUCTION=false --env ROOT_PASSWORD=123123 --env SECRET_KEY=abcabcabca -v (pwd):/code ***REMOVED***/fizz


    def tag(self):
        """Tag git version and docker version"""
        build()
        # todo
        # git tag
        # docker tag -f ***REMOVED***/fizz:latest ***REMOVED***/***REMOVED***/***REMOVED***:latest


    def test(self):
        """Build and run Unit Tests"""
        build()
        # todo


    def stage(self):
        """Deploy on test servers"""
        build()
        tag()
        # todo
        # docker push ***REMOVED***/***REMOVED***/***REMOVED***:latest
        # tell newrelic a deployment is happening
        # tell tutum to reload/redeploy


    def deploy(self):
        """Deploy on live servers"""
        build()
        # todo
        # tag?
        # docker push
        # tell newrelic a deployment is happening
        # tell tutum to reload/redeploy

if __name__ == '__main__':
    d = Deployer()

    if len(sys.argv) > 1 and sys.argv[1] in dir(d):
        getattr(d, sys.argv[1])
    else:
        print("USAGE:")
        print("\t%s %s" % (sys.argv[0], dir(d)))
        exit(0)
