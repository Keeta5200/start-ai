FROM node:20-alpine
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build && \
    cp -r public .next/standalone/ && \
    cp -r .next/static .next/standalone/.next/

ENV NODE_ENV=production
ENV PORT=8080
ENV HOSTNAME=0.0.0.0

EXPOSE 8080

CMD ["node", ".next/standalone/server.js"]
