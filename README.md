# Buku Latihan

Practicing Past Year Papers online. This is the backend of the application. Made in Django 3.2. Developed in Docker-Compose with [Cookiecutter](https://cookiecutter-django.readthedocs.io/)

## Development

After `git clone`, run the following commands in the `buku-latihan` directory:

`docker-compose -f local.yml build` to build the images.

`docker-compose -f local.yml up` to bring up the development environment.

### Execute Management commands

`docker-compose -f local.yml run --rm django python manage.py migrate`

`docker-compose -f local.yml run --rm django python manage.py createsuperuser`


## Deployment

Somewhere in Heroku. [Relevant docs](https://cookiecutter-django.readthedocs.io/en/latest/deployment-on-heroku.html#commands-to-run).
