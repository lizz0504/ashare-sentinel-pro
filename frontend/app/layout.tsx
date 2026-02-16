import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "LofX Capital - 智能投资分析平台",
  description: "基于多源数据融合的智能投研平台，为专业投资者提供深度市场洞察与决策支持",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
