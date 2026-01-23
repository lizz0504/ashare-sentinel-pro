import Link from "next/link"

export default function HomePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="text-center space-y-8">
        <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
          Fintech Platform
        </h1>
        <p className="text-xl text-slate-400">
          Investment Research & Intelligence Monitoring
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/login"
            className="px-8 py-3 rounded-lg bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-700 hover:to-emerald-700 text-white font-medium transition-all"
          >
            Sign In
          </Link>
          <Link
            href="/dashboard"
            className="px-8 py-3 rounded-lg border border-slate-700 hover:bg-slate-800 text-slate-300 font-medium transition-all"
          >
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}
