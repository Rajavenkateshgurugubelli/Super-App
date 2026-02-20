# Build Stage
FROM node:22-alpine AS build
WORKDIR /app/frontend/wallet

# Install dependencies first (cached layer)
COPY frontend/wallet/package*.json ./
RUN npm install --legacy-peer-deps

# Copy wallet source (Button is now vendored locally — no shared-ui needed)
COPY frontend/wallet ./
RUN npm run build

# Serve Stage
FROM nginx:alpine
COPY --from=build /app/frontend/wallet/dist /usr/share/nginx/html
COPY frontend/wallet/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
