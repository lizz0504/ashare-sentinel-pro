'use client'

import { useEffect, useState, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase/client"
import { Database } from "@/types/supabase"

type Report = Database["public"]["Tables"]["reports"]["Row"]
type Message = {
  role: "user" | "assistant"
  content: string
}

export default function ReportChatPage() {
  const params = useParams()
  const router = useRouter()
  const reportId = params.id as string

  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 加载报告信息
  useEffect(() => {
    const fetchReport = async () => {
      try {
        const { data, error } = await supabase
          .from("reports")
          .select("*")
          .eq("id", reportId)
          .single()

        if (error) throw error
        setReport(data)
      } catch (error) {
        console.error("Error loading report:", error)
        router.push("/dashboard/research")
      } finally {
        setLoading(false)
      }
    }

    fetchReport()
  }, [reportId, router])

  // 发送消息
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    console.log("[DEBUG] Submit called, input:", input, "sending:", sending)

    if (!input.trim() || sending) {
      console.log("[DEBUG] Submit blocked - input empty or already sending")
      return
    }

    const userMessage = input.trim()
    setInput("")
    setSending(true)

    console.log("[DEBUG] Sending message:", userMessage)

    // 添加用户消息
    setMessages((prev) => [...prev, { role: "user", content: userMessage }])

    try {
      console.log("[DEBUG] Fetching from backend...")
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          report_id: reportId,
          query: userMessage,
        }),
      })

      console.log("[DEBUG] Response status:", response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error("[DEBUG] Response error:", errorText)
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const data = await response.json()
      console.log("[DEBUG] Response data:", data)
      console.log("[DEBUG] Answer content:", data.answer)

      // 添加助手回复
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }])
      console.log("[DEBUG] Added assistant message to state")
    } catch (error) {
      console.error("[DEBUG] Fetch error:", error)
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `抱歉，发生了错误：${error instanceof Error ? error.message : "未知错误"}` },
      ])
    } finally {
      setSending(false)
      console.log("[DEBUG] Request completed")
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-500">Report not found</div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 左侧：研报信息 */}
      <div className="w-80 bg-white border-r border-gray-200 p-6 overflow-y-auto">
        <button
          onClick={() => router.push("/dashboard/research")}
          className="mb-4 text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          ← Back to Research
        </button>

        <h2 className="text-lg font-semibold mb-4">Report Info</h2>

        <div className="space-y-3 text-sm">
          <div>
            <div className="font-medium text-gray-700">Title</div>
            <div className="text-gray-600 break-words">{report.title}</div>
          </div>

          <div>
            <div className="font-medium text-gray-700">Filename</div>
            <div className="text-gray-600 break-words">{report.filename}</div>
          </div>

          <div>
            <div className="font-medium text-gray-700">Status</div>
            <div className="inline-flex items-center px-2 py-1 rounded text-xs font-medium
              {report.status === 'completed' ? 'bg-green-100 text-green-700' : ''}
              {report.status === 'processing' ? 'bg-yellow-100 text-yellow-700' : ''}
              {report.status === 'failed' ? 'bg-red-100 text-red-700' : ''}">
              {report.status}
            </div>
          </div>

          <div>
            <div className="font-medium text-gray-700">File Size</div>
            <div className="text-gray-600">
              {report.file_size ? (report.file_size / 1024).toFixed(2) : "0"} KB
            </div>
          </div>

          <div>
            <div className="font-medium text-gray-700">Uploaded</div>
            <div className="text-gray-600">
              {new Date(report.uploaded_at).toLocaleString()}
            </div>
          </div>

          {report.summary && (
            <div>
              <div className="font-medium text-gray-700 mb-1">AI Summary</div>
              <div className="text-gray-600 text-xs bg-gray-50 p-2 rounded">
                {report.summary}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 右侧：聊天界面 */}
      <div className="flex-1 flex flex-col">
        {/* 顶部标题栏 */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <h1 className="text-xl font-semibold">Chat with Report</h1>
          <p className="text-sm text-gray-500 mt-1">
            Ask questions about this research report
          </p>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-400 mt-20">
              <p className="text-lg mb-2">Start a conversation</p>
              <p className="text-sm">Ask a question about this report</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-2xl rounded-lg px-4 py-3 ${
                    message.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-black border border-gray-400"
                  }`}
                  style={message.role === "assistant" ? { backgroundColor: "#e5e7eb", color: "#000000" } : {}}
                >
                  <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                </div>
              </div>
            ))
          )}

          {sending && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入框 */}
        <div className="bg-white border-t border-gray-200 p-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about this report..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
