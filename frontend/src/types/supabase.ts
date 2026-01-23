/**
 * Supabase Database Types
 *
 * 这是一个占位符文件，用于定义 Supabase 数据库的 TypeScript 类型
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      reports: {
        Row: {
          id: string
          title: string
          filename: string
          status: "processing" | "completed" | "failed"
          file_size: number | null
          uploaded_at: string
          updated_at: string
          user_id: string | null
          summary: string | null
        }
        Insert: {
          id?: string
          title: string
          filename: string
          status?: "processing" | "completed" | "failed"
          file_size?: number | null
          uploaded_at?: string
          updated_at?: string
          user_id?: string | null
          summary?: string | null
        }
        Update: {
          id?: string
          title?: string
          filename?: string
          status?: "processing" | "completed" | "failed"
          file_size?: number | null
          uploaded_at?: string
          updated_at?: string
          user_id?: string | null
          summary?: string | null
        }
      }
      report_chunks: {
        Row: {
          id: string
          report_id: string
          content: string
          page_number: number
          created_at: string
        }
        Insert: {
          id?: string
          report_id: string
          content: string
          page_number: number
          created_at?: string
        }
        Update: {
          id?: string
          report_id?: string
          content?: string
          page_number?: number
          created_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}
