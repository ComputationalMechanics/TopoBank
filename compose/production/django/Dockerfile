FROM continuumio/miniconda3
# FROM ubuntu:18.04
#FROM python:3.7-alpine

ENV PYTHONUNBUFFERED 1

#
# System dependencies for Python + Django
#
RUN apt-get update \
  && apt-get install --yes apt-utils \
  && apt-get install --yes libfftw3-3 libfftw3-dev libopenblas-dev libpq-dev gcc g++ gettext \
  # Pillow requirements
  && apt-get install --yes libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libtiff-dev tk-dev tcl-dev librabbitmq-dev

# clean up image
RUN apt-get -qy autoremove

#
# Extra requirements for exporting plots in bokeh
#
RUN apt-get install --yes libgtk-3-0 libdbus-glib-1-2
RUN conda install -c conda-forge firefox geckodriver

#
# Create user and group
#
RUN addgroup django \
    && adduser --ingroup django --gecos "" --disabled-password django
# or using --system? Problems with permissions?
# celeryworker should not run as root, refuses to work
#
# TODO use --disabled-login ??

#
# Install requirements for TopoBank
#
COPY ./requirements /requirements
WORKDIR /
RUN pip install --no-cache-dir -r /requirements/production.txt --ignore-installed && rm -Rf /requirements

COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r//' /entrypoint
RUN chmod +x /entrypoint
RUN chown django /entrypoint

COPY ./compose/production/django/start /start
RUN sed -i 's/\r//' /start
RUN chmod +x /start
RUN chown django /start

COPY ./compose/production/django/celery/worker/start /start-celeryworker
RUN sed -i 's/\r//' /start-celeryworker
RUN chmod +x /start-celeryworker
RUN chown django /start-celeryworker

COPY ./compose/production/django/celery/beat/start /start-celerybeat
RUN sed -i 's/\r//' /start-celerybeat
RUN chmod +x /start-celerybeat
RUN chown django /start-celerybeat

COPY ./compose/production/django/celery/flower/start /start-flower
RUN sed -i 's/\r//' /start-flower
RUN chmod +x /start-flower

#
# Prepare application code
#
COPY . /app
# TODO is the following needed?
RUN mkdir -p /app/media/topographies
RUN chown -R django /app

#
# Finalize..
#
WORKDIR /app

USER django

ENTRYPOINT ["/entrypoint"]
