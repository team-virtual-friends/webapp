# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8-slim

# Use an official NVIDIA CUDA base image that includes cuBLAS and cuDNN for CUDA 11
# FROM nvidia/cuda:11.0-base
# # nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
# # nvidia/cuda:11.0-base

RUN apt update
# Used to tweak the voice stream.
RUN apt install -y ffmpeg

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN pip install -r requirements.txt

EXPOSE 8080
EXPOSE $PORT

## allow logs
ENV PYTHONUNBUFFERED=1
ENV ENV=STAGING

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app --timeout 60
