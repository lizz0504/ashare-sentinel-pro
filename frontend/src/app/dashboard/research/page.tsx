"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Upload, FileText, Loader2, Clock, CheckCircle2, AlertCircle, Sparkles, MessageSquare } from "lucide-react"
import { supabase } from "@/lib/supabase/client"

interface Report {
  id: string
  title: string
  filename: string
  status: "processing" | "completed" | "failed"
  uploaded_at: string
  file_size: number | null
  summary: string | null
}

export default function ResearchPage() {
  const router = useRouter()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [uploadResult, setUploadResult] = useState<{
    taskId: string
    filename: string
    size: number
  } | null>(null)
  const [reports, setReports] = useState<Report[]>([])
  const [isLoadingReports, setIsLoadingReports] = useState(true)

  const loadReports = async () => {
    try {
      const { data, error } = await supabase
        .from("reports")
        .select("*")
        .order("uploaded_at", { ascending: false })

      if (error) throw error
      setReports(data || [])
    } catch (error) {
      console.error("Error loading reports:", error)
    } finally {
      setIsLoadingReports(false)
    }
  }

  // 加载报告列表
  useEffect(() => {
    loadReports()

    // 设置实时订阅
    const channel = supabase
      .channel("reports-changes")
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "reports",
        },
        () => {
          loadReports()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setUploadResult(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      alert("请先选择文件")
      return
    }

    setIsLoading(true)
    setUploadResult(null)

    try {
      const formData = new FormData()
      formData.append("file", selectedFile)

      console.log("[DEBUG] 开始上传:", selectedFile.name, selectedFile.size)

      const response = await fetch("http://localhost:8000/api/v1/analyze/upload", {
        method: "POST",
        body: formData,
      })

      console.log("[DEBUG] 响应状态:", response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error("[ERROR] 服务器错误:", errorText)
        throw new Error(`上传失败: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      console.log("[DEBUG] 上传成功:", data)

      setUploadResult({
        taskId: data.task_id,
        filename: data.filename,
        size: data.size,
      })

      // 刷新报告列表
      loadReports()
    } catch (error) {
      console.error("[ERROR] 上传错误:", error)
      alert(`上传失败: ${error instanceof Error ? error.message : "未知错误"}`)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusIcon = (status: Report["status"]) => {
    switch (status) {
      case "processing":
        return <Loader2 className="w-4 h-4 animate-spin text-yellow-400" />
      case "completed":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />
      case "failed":
        return <AlertCircle className="w-4 h-4 text-red-400" />
    }
  }

  const getStatusBadge = (status: Report["status"]) => {
    const styles = {
      processing: "bg-yellow-900/20 text-yellow-400 border-yellow-800",
      completed: "bg-emerald-900/20 text-emerald-400 border-emerald-800",
      failed: "bg-red-900/20 text-red-400 border-red-800",
    }
    return (
      <span className={`px-2 py-1 rounded-md text-xs font-medium border ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold text-slate-100">
          深度投研中心 / Research Hub
        </h1>
        <p className="mt-2 text-slate-400">
          Upload research reports for AI-powered analysis and insights
        </p>
      </div>

      {/* Upload Card */}
      <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100">
            <FileText className="w-5 h-5 text-blue-400" />
            Upload Research Report
          </CardTitle>
          <CardDescription className="text-slate-400">
            Supported formats: PDF (Max 10MB)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* File Input */}
          <div className="space-y-2">
            <label htmlFor="file-upload" className="text-sm font-medium text-slate-300">
              Select File
            </label>
            <div className="flex items-center gap-4">
              <Input
                id="file-upload"
                type="file"
                onChange={handleFileChange}
                accept=".pdf"
                disabled={isLoading}
                className="bg-slate-950/50 border-slate-700 text-slate-100 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-slate-800 file:text-blue-400 hover:file:bg-slate-700"
              />
            </div>
            {selectedFile && (
              <p className="text-sm text-slate-400">
                Selected: <span className="text-slate-200">{selectedFile.name}</span> (
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
          </div>

          {/* Upload Button */}
          <Button
            onClick={handleUpload}
            disabled={!selectedFile || isLoading}
            className="w-full bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-700 hover:to-emerald-700 text-white font-medium"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Start Analysis
              </>
            )}
          </Button>

          {/* Upload Result */}
          {uploadResult && (
            <div className="p-4 rounded-lg bg-emerald-900/20 border border-emerald-800">
              <p className="text-sm font-medium text-emerald-400 mb-2">Upload Successful!</p>
              <div className="space-y-1 text-sm text-slate-300">
                <p>Task ID: <code className="px-2 py-0.5 rounded bg-slate-950">{uploadResult.taskId}</code></p>
                <p>Filename: {uploadResult.filename}</p>
                <p>Size: {(uploadResult.size / 1024).toFixed(2)} KB</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Reports List */}
      <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100">
            <Clock className="w-5 h-5 text-blue-400" />
            Recent Reports
          </CardTitle>
          <CardDescription className="text-slate-400">
            View and manage your uploaded research reports
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingReports ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : reports.length === 0 ? (
            <div className="text-center py-8 text-slate-400">
              No reports uploaded yet. Upload your first PDF to get started.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-slate-400">Title</TableHead>
                  <TableHead className="text-slate-400">Status</TableHead>
                  <TableHead className="text-slate-400">AI Insight</TableHead>
                  <TableHead className="text-slate-400">Uploaded</TableHead>
                  <TableHead className="text-slate-400 text-right">Size</TableHead>
                  <TableHead className="text-slate-400 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((report) => (
                  <TableRow
                    key={report.id}
                    className="cursor-pointer hover:bg-slate-800/50 transition-colors"
                    onClick={() => router.push(`/dashboard/research/${report.id}`)}
                  >
                    <TableCell className="font-medium text-slate-200">{report.title}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(report.status)}
                        {getStatusBadge(report.status)}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-md">
                      {report.summary ? (
                        <div
                          className="group relative inline-block"
                          title={report.summary}
                        >
                          <div className="flex items-start gap-2">
                            <Sparkles className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                            <p className="text-sm text-slate-300 line-clamp-2">
                              {report.summary.length > 60
                                ? `${report.summary.slice(0, 60)}...`
                                : report.summary}
                            </p>
                          </div>
                          {/* Tooltip */}
                          <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block z-10">
                            <div className="bg-slate-950 border border-slate-700 rounded-lg p-3 shadow-xl max-w-sm">
                              <p className="text-sm text-slate-200 whitespace-pre-wrap">
                                {report.summary}
                              </p>
                            </div>
                          </div>
                        </div>
                      ) : report.status === "completed" ? (
                        <span className="text-sm text-slate-500 italic">No Summary</span>
                      ) : (
                        <span className="text-sm text-slate-600 italic">Pending...</span>
                      )}
                    </TableCell>
                    <TableCell className="text-slate-400">
                      {new Date(report.uploaded_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-slate-400 text-right">
                      {report.file_size ? `${(report.file_size / 1024).toFixed(0)} KB` : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-blue-400 hover:text-blue-300 hover:bg-blue-900/20"
                        onClick={(e) => {
                          e.stopPropagation()
                          router.push(`/dashboard/research/${report.id}`)
                        }}
                      >
                        <MessageSquare className="w-4 h-4 mr-1" />
                        Chat
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
