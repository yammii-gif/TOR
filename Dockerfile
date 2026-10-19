# syntax=docker/dockerfile:1
# Hugging Face Spaces: upload this single file to a Docker / Blank Space.
# The application is the existing, tested GitHub snapshot, pinned and checked.
FROM node:24-bookworm-slim AS frontend
ADD --checksum=sha256:1603ef8c345ee73eacdfb206d52bc6440c5788418f789124089f6043376b4961 https://codeload.github.com/yammii-gif/TOR/tar.gz/140ab3477b369c7e04603276635799b6e23638da /tmp/source.tar.gz
WORKDIR /src
RUN tar -xzf /tmp/source.tar.gz --strip-components=1 -C /src
WORKDIR /src/frontend
RUN npm ci --no-audit --no-fund
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY --from=frontend /src/backend /app/backend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY --from=frontend /src/frontend/node_modules /app/frontend/node_modules
COPY --from=frontend --chown=1000:1000 /src/frontend/.next /app/frontend/.next
COPY --from=frontend /src/frontend/package.json /app/frontend/package.json
COPY --from=frontend /src/scripts/start-online.sh /app/scripts/start-online.sh
ENV PORT=7860 \
    BACKEND_URL=http://127.0.0.1:8000 \
    DATABASE_URL=sqlite:////tmp/renal-smart.db \
    COOKIE_SECURE=true \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
USER appuser
EXPOSE 7860
CMD ["bash", "/app/scripts/start-online.sh"]
