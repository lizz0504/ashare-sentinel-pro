"use client"

import Link from "next/link"
import { BarChart3, LayoutDashboard, Briefcase, Users, Zap } from "lucide-react"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const navItems = [
    {
      href: "/dashboard",
      icon: LayoutDashboard,
      label: "Dashboard",
    },
    {
      href: "/dashboard/research",
      icon: BarChart3,
      label: "Research",
      sublabel: "投研中心",
    },
    {
      href: "/dashboard/portfolio",
      icon: Briefcase,
      label: "Portfolio",
      sublabel: "智能股票池",
    },
    {
      href: "/dashboard/ic",
      icon: Users,
      label: "IC Committee",
      sublabel: "IC投委会",
    },
    {
      href: "/dashboard/guru",
      icon: Zap,
      label: "Guru Watcher",
      sublabel: "大V监控",
    },
  ]

  return (
    <div className="flex h-screen bg-slate-950">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900/50 border-r border-slate-800 backdrop-blur-sm">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-slate-800">
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              Fintech Platform
            </h1>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-all group"
                >
                  <Icon className="w-5 h-5 group-hover:text-blue-400 transition-colors" />
                  <div className="flex flex-col">
                    <span className="font-medium">{item.label}</span>
                    {item.sublabel && (
                      <span className="text-xs text-slate-500 group-hover:text-slate-400">
                        {item.sublabel}
                      </span>
                    )}
                  </div>
                </Link>
              )
            })}
          </nav>

          {/* User Info */}
          <div className="p-4 border-t border-slate-800">
            <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-slate-800/50">
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-emerald-500 flex items-center justify-center text-white font-medium text-sm">
                U
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-medium text-slate-200">User</span>
                <span className="text-xs text-slate-500">user@example.com</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
