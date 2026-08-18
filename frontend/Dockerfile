FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* variables are inlined into the client bundle at BUILD time by
# `next build` — setting them as a runtime `environment:` in docker-compose
# has NO effect (a real bug caught in review: docker-compose.demo.yml was
# setting NEXT_PUBLIC_API_URL at container-start time, which silently did
# nothing; it only "worked" by coincidence because the fallback in
# lib/api.ts happened to match). This ARG + ENV pair makes the value
# actually flow in via `docker build --build-arg` / compose's `build.args`.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"]
