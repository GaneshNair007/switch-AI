FROM node:24.18.0-bookworm-slim
ENV NODE_ENV=production
WORKDIR /app
COPY voice/package.json voice/package-lock.json ./voice/
RUN npm ci --prefix voice --omit=dev --ignore-scripts \
    && groupadd --gid 10001 shipcourt \
    && useradd --uid 10001 --gid 10001 --no-create-home shipcourt \
    && mkdir -p /app/.runtime && chown shipcourt:shipcourt /app/.runtime
COPY voice/*.mjs ./voice/
USER 10001:10001
CMD ["node", "voice/gateway.mjs"]
