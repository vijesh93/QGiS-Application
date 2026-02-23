# Use a slim Python 3.10 base image
FROM python:3.11-slim

# Allow build-time proxy args to be passed via docker-compose build args
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Export proxy vars into the image environment so apt/pip use them during build
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

# Prevent Python from writing .pyc files and keep stdout unbuffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for OpenCV and spatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    build-essential \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Set GDAL paths for rasterio
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# If needed: ipython kernel
# RUN python -m ipykernel install --name "raster_env" --display-name "Python (raster_env)"

# Copy the rest of your application code
COPY . .

# Keep the container alive so you can run scripts against it
CMD ["tail", "-f", "/dev/null"]