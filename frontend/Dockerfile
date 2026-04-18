FROM node:20-alpine
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build && \
    mkdir -p .next/standalone/public && \
    (cp -r public/. .next/standalone/public/ 2>/dev/null || true) && \
    cp -r .next/static .next/standalone/.next/ && \
    cp -r .next/standalone/. ./

ENV NODE_ENV=production
ENV PORT=8080
ENV HOSTNAME=0.0.0.0

EXPOSE 8080

CMD ["node", "server.js"]
