# 构建阶段
FROM node:18-slim AS builder
WORKDIR /app

# 支持外部传入 VITE_APP_ENV
ARG VITE_APP_ENV=docker
ENV VITE_APP_ENV=$VITE_APP_ENV

COPY . .
RUN npm config set registry https://registry.npmmirror.com
RUN npm install
RUN npm run build:docker

# 运行阶段
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

COPY --from=builder /app/dist .
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
