# Stage 1 - Build Flask app
#FROM python:3.9-slim-buster AS flask_app
FROM python:3.9-slim-buster AS flask_app

# Set the working directory to /app
WORKDIR /src

# Copy the current directory contents into the container at /app and install additional packages
COPY src/ /src/
COPY config/ /config/
RUN ls --recursive /src/
RUN ls --recursive /config/
RUN apt-get update && \
    apt-get upgrade -y     
RUN apt-get install -y locales locales-all

# Install any needed packages specified in requirements.txt
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Set environment variables
ENV UPLOAD_FOLDER ./static/data
ENV PYTHONUNBUFFERED 1
ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8

# Expose port 5000 for the Flask app
EXPOSE 5000

# Run app.py when the container launches
#COPY startup.sh /
#RUN chmod +x /startup.sh
#CMD ["/startup.sh"]


# Stage 2 - Build dask
FROM ghcr.io/dask/dask:2023.4.0-py3.9 AS dask

# Copy requirements.txt from stage
COPY requirements.txt requirements.txt
RUN  pip3 install -r requirements.txt
