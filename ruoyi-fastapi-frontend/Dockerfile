# 构建阶段（使用固定 LTS 版本，避免浮动标签导致缓存失效）
FROM node:22-slim AS builder
WORKDIR /app

# 支持外部传入 VITE_APP_ENV
ARG VITE_APP_ENV=docker
ENV VITE_APP_ENV=$VITE_APP_ENV

# 增加 Node.js 内存上限（Vite 构建大项目时需要）
ENV NODE_OPTIONS="--max-old-space-size=8192"

COPY . .
# 优先使用 npmmirror 镜像，如果包不存在则回退到官方源
RUN npm install --registry=https://registry.npmjs.org/
RUN npm run build:docker

# 运行阶段
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

COPY --from=builder /app/dist .
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
