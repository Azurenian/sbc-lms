# Dockerfile for PayloadCMS + Next.js standalone build with pnpm/native module fixes

FROM node:22.12.0-slim AS base

# Stage 1: Dependency install
FROM base AS deps
WORKDIR /app

RUN npm install -g corepack@latest && corepack enable

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./

RUN \
  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i; \
  else echo "Lockfile not found." && exit 1; \
  fi

# Stage 2: Build application
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm install -g corepack@latest && corepack enable

# Clean stale builds
RUN rm -rf .next

RUN \
  if [ -f yarn.lock ]; then yarn run build; \
  elif [ -f package-lock.json ]; then npm run build; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm run build; \
  else echo "Lockfile not found." && exit 1; \
  fi

# Stage 3: Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
# ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# ✅ Copy node_modules fully (preserve native modules like libsql)
# This might be a necessary workaround for `@libsql/client` tracing issues
COPY --from=builder /app/node_modules ./node_modules

# ✅ Workaround: copy standalone with root, then chown
USER root
COPY --from=builder /app/.next/standalone ./standalone

# Copy static and public assets to the correct location within the standalone folder
COPY --from=builder /app/.next/static ./standalone/.next/static
COPY --from=builder /app/public ./standalone/public

# Set correct permissions for the entire standalone directory
RUN chown -R nextjs:nodejs ./standalone

USER nextjs

EXPOSE 3000
ENV PORT 3000

# ✅ Run standalone server.js from correct folder
CMD HOSTNAME="0.0.0.0" node ./standalone/server.js
