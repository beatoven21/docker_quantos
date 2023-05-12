#!/bin/bash
docker build -t flask_app -f Dockerfile --target=flask_app . # to create the custom image with flask application
docker build -t dask -f Dockerfile --target=dask . # to create the custom image with dask and requirements installed 
docker network create dask # create network for dask
docker network create flask-net # create network for flask
docker compose -f docker_compose.yml up -d   #to build the infra that includes 3 containers 1x scheduler 1x or more containers as Workers and 1x flask for quantos application.

