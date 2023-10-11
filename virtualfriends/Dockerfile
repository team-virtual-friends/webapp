# Use an official NVIDIA CUDA base image that includes cuBLAS and cuDNN for CUDA 11
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Update and install dependencies
RUN apt update && \
    apt install -y python3 python3-pip ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install Python dependencies.
RUN pip3 install -r requirements.txt

# Expose the required ports
EXPOSE 8080
EXPOSE $PORT

# Set environment variables for logging and environment stage
ENV PYTHONUNBUFFERED=1
ENV ENV=STAGING

# Run the web service on container startup using gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app --timeout 60

