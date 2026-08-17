FROM node:22-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

ARG VITE_GOOGLE_MAPS_API_KEY=""
ARG VITE_API_BASE_URL="/api/v1"
ARG VITE_EVENT_SOURCE="api"
ARG VITE_AGENT_SOURCE="agent"

ENV VITE_GOOGLE_MAPS_API_KEY=${VITE_GOOGLE_MAPS_API_KEY}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_EVENT_SOURCE=${VITE_EVENT_SOURCE}
ENV VITE_AGENT_SOURCE=${VITE_AGENT_SOURCE}

RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
