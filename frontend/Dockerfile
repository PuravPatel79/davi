# STAGE 1: Build the React application
FROM node:18-alpine AS build

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application's source code
COPY . .

# Build the application for production
# This command creates the /app/dist folder
RUN npm run build

# STAGE 2: Serve the built application with Nginx
FROM nginx:stable-alpine

# Copy the built files from the correct folder (/app/dist)
COPY --from=build /app/dist /usr/share/nginx/html

# The .template suffix tells the Nginx entrypoint script to process it and substitute any environment variables it finds
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Expose port 80
EXPOSE 80