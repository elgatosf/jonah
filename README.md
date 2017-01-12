# Django Deployment via Docker

This repository is a fork of [Joe Mornin's excellent `django-docker`](https://github.com/morninj/django-docker). To deploy a django project with this fork, your Django project has to be named `ddp`.
  
Symlink the Dockerfile and .dockerignore into your root directory:

    ln -s deployment/Dockerfile .
    ln -s deployment/.dockerignore .

You can also optionally have a file called `supervisord_local.conf`. Its contents will be appended to 
`supervisord.conf` on build.

## deploy.py

You can use the `deploy.py` script to automatically build, run, and deploy the Docker container. Before you run `deploy.py`, check wether the `deploy.ini` file contains the correct configuration info for your project. Please also make sure that you are in a shell environment that can run Docker commands.

The following is a list of commands you can use:

- `deploy.py build` Builds the docker image
- `deploy.py develop` Builds the docker image and runs a development server on it. You can access the server by pointing your browser to your Docker machine's external IP (run `docker-machine env default` to find out the IP)
- `deploy.py reload` Reloads the running development server
- `deploy.py shell` Opens a shell within the container
- `deploy.py stage` Builds the image, pushes it to the staging repository and calls the staging reload web hook
- `deploy.py stop` Stops any running containers of this image
- `deploy.py test` Builds and runs tests
- `deploy.py deploy` Builds the image and pushes it to the production repository. Does not call any web hooks
