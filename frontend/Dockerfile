FROM python:3.12-slim AS public-exercises
WORKDIR /workspace
COPY frontend/scripts/export-exercises.py frontend/scripts/export-exercises.py
COPY backend/app/exercises/seed_data.py backend/app/exercises/seed_data.py
COPY backend/app/exercises/enums.py backend/app/exercises/enums.py
COPY backend/app/exercises/curated_safety_notes.py backend/app/exercises/curated_safety_notes.py
COPY backend/app/exercises/media_metadata.py backend/app/exercises/media_metadata.py
COPY backend/app/exercises/catalog_categories.py backend/app/exercises/catalog_categories.py
COPY backend/app/exercises/taxonomy.py backend/app/exercises/taxonomy.py
COPY backend/app/exercises/publication_slugs.json backend/app/exercises/publication_slugs.json
COPY frontend/src/seo/exercise-publications.json frontend/src/seo/exercise-publications.json
RUN mkdir -p frontend/src/seo && python3 frontend/scripts/export-exercises.py

FROM node:20.19.4-bookworm-slim AS build

ARG VITE_MEDIA_PUBLIC_BASE_URL=
ENV VITE_MEDIA_PUBLIC_BASE_URL=${VITE_MEDIA_PUBLIC_BASE_URL}
ARG VITE_GOOGLE_CLIENT_ID=
ENV VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID}

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package.json
COPY packages/fitician-core/package.json packages/fitician-core/package.json
COPY vendor vendor
RUN npm ci

COPY frontend frontend
COPY packages packages
COPY --from=public-exercises /workspace/frontend/src/seo/exercise-data.json frontend/src/seo/exercise-data.json
COPY --from=public-exercises /workspace/frontend/src/seo/exercise-categories.json frontend/src/seo/exercise-categories.json
RUN npm run build:core && npm run prepare:mediapipe --workspace frontend && npm exec --workspace frontend -- tsc -b && npm exec --workspace frontend -- vite build && SEO_SERVER=1 npm exec --workspace frontend -- vite build --ssr src/seo/render.tsx --outDir dist-server
WORKDIR /workspace/frontend
RUN node scripts/prerender.mjs

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/frontend/dist /usr/share/nginx/html

COPY --from=build /workspace/frontend/dist/nginx-member-routes.conf /etc/nginx/conf.d/member-routes.inc

EXPOSE 80
