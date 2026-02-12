FROM node:20-alpine

# Allow build-time proxy args to be passed via docker-compose build args
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Export proxy vars into the image environment so apt/pip use them during build
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

WORKDIR /app

# Install dependencies first (for faster builds)
COPY package.json ./
RUN npm install

# Copy the rest of the code
COPY . .

# Expose Vite's default port
EXPOSE 5173

CMD ["npm", "run", "dev"]