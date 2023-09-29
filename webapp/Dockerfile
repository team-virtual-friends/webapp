# gcloud builds --project ysong-chat submit --tag gcr.io/ysong-chat/webapp:$(git rev-parse --short HEAD)-$(openssl rand -hex 4) .

FROM python:3.8-slim

# Metadata as described above
LABEL maintainer="yisong0623@gmail.com"

# Set environment variables for Python
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

# Define environment variables for Gunicorn
ENV GUNICORN_CMD="gunicorn"
ENV APP_MODULE="app:app"
ENV WORKER_COUNT="4"

# Run the application using Gunicorn
CMD $GUNICORN_CMD -w $WORKER_COUNT -b 0.0.0.0:8000 $APP_MODULE