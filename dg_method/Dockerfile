# Use Python 3.11 as base image to match the main backend
FROM python:3.11.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for mesh generation and scientific computing
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    gmsh \
    && rm -rf /var/lib/apt/lists/*

# Copy method package directory
COPY dg_method /app/dg_method

# Install the method package
RUN pip install --no-cache-dir /app/dg_method

WORKDIR /app/dg_method

# Default command to run the containerized DG method
CMD ["python", "-m", "dg_interface"]
