# ============================================
# 前端Dockerfile - Next.js Standalone模式
# ============================================

# 构建阶段
FROM node:18-alpine AS builder

WORKDIR /app

# 设置npm镜像源（加速国内构建）
RUN npm config set registry https://registry.npmmirror.com

# 构建参数（从docker-compose或命令行传入）
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_URL

# 复制package文件
COPY package*.json ./

# 安装依赖（构建需要所有依赖）
RUN npm ci && \
    npm cache clean --force

# 复制源代码
COPY . .

# 设置构建时环境变量
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# 构建Next.js（standalone模式）
RUN npm run build

# 生产阶段
FROM node:18-alpine AS runner

WORKDIR /app

# 创建非root用户
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# 设置环境变量
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# 复制必要的文件
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/.next/server/pages ./app/.next/server/pages

# 设置权限
USER nextjs

EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# 启动Next.js standalone服务器
CMD ["node", "server.js"]
