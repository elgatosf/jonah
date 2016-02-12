local_repository_name = '***REMOVED***'
local_image_name = 'fizz'

testing_repository_name = '***REMOVED***/***REMOVED***/***REMOVED***'


def build():
    # docker build -t ***REMOVED***/fizz .
    pass


def develop():
    build()
    # docker run -d -p 80:80 --env DJANGO_PRODUCTION=false --env ROOT_PASSWORD=123123 --env SECRET_KEY=abcabcabca -v (pwd):/code ***REMOVED***/fizz


def tag():
    build()
    # git tag
    # docker tag -f ***REMOVED***/fizz:latest ***REMOVED***/***REMOVED***/***REMOVED***:latest


def test():
    build()
    # todo


def deploy_test():
    build()
    tag()
    # docker push ***REMOVED***/***REMOVED***/***REMOVED***:latest
    # tell newrelic a deployment is happening
    # tell tutum to reload/redeploy


def deploy_live():
    build()
    # tag?
    # docker push
    # tell newrelic a deployment is happening
    # tell tutum to reload/redeploy

