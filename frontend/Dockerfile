FROM node:20.19.4-bookworm-slim AS build

ARG VITE_MEDIA_PUBLIC_BASE_URL=
ENV VITE_MEDIA_PUBLIC_BASE_URL=${VITE_MEDIA_PUBLIC_BASE_URL}
ARG VITE_GOOGLE_CLIENT_ID=
ENV VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID}

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package.json
COPY packages/fitician-core/package.json packages/fitician-core/package.json
RUN npm ci

COPY frontend frontend
COPY packages packages
RUN npm run build:core && npm run build --workspace frontend

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/frontend/dist /usr/share/nginx/html

EXPOSE 80
