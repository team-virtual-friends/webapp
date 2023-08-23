# Use an official Python runtime as the base image
FROM python:3.9-slim

# Metadata as described above
LABEL maintainer="yisong0623@gmail.com"

# Set environment variables:
# 1. Set PYTHONUNBUFFERED so that Python output is logged immediately.
# 2. Set PYTHONDONTWRITEBYTECODE so that Python doesn't try to write .pyc files.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable for Gunicorn
ENV GUNICORN_CMD="gunicorn"
ENV APP_MODULE="app:app"
ENV WORKER_COUNT="4"

# Run the application using Gunicorn
CMD $GUNICORN_CMD -w $WORKER_COUNT -b 0.0.0.0:8000 $APP_MODULE
