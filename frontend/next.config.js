/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // 启用standalone输出用于Docker
  reactStrictMode: true,
  images: {
    unoptimized: true, // Docker环境禁用图片优化
  },
}

module.exports = nextConfig
