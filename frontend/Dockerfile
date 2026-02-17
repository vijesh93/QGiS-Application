# FROM node:20-alpine
FROM node:20-slim

# Allow build-time proxy args to be passed via docker-compose build args
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Export proxy vars into the image environment so apt/pip use them during build
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

WORKDIR /app

# Install system dependencies if needed (e.g., for some canvas/map libs)
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies (for faster builds) and copy package files first for better caching
COPY package.json ./
RUN npm install

# Copy the rest of the code
COPY . .

# Expose Vite's default port
EXPOSE 5173

CMD ["npm", "run", "dev", "--host"]