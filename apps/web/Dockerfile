FROM node:24-alpine AS build
WORKDIR /app
RUN npm install --global pnpm@11.20.0
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web
COPY packages/contracts packages/contracts
ENV INTERNAL_API_URL=http://server:4000
ENV INTERNAL_HLS_URL=http://mediamtx:8888
RUN pnpm --filter @phij/web build

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production
ENV INTERNAL_API_URL=http://server:4000
ENV INTERNAL_HLS_URL=http://mediamtx:8888
COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/.next/static ./apps/web/.next/static
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
