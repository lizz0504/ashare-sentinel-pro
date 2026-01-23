"""
OCR Service - PDF Content Extraction

使用 PyMuPDF (fitz) 提取 PDF 文本内容并存储到 Supabase
"""

import fitz
from supabase import Client

from app.core.db import get_db_client
from app.services.llm_service import generate_summary, create_embedding


def process_pdf(file_bytes: bytes, filename: str, user_id: str | None = None) -> str:
    """
    处理 PDF 文件：提取文本并存储到数据库

    Args:
        file_bytes: PDF 文件二进制内容
        filename: 文件名
        user_id: 用户 ID（可选）

    Returns:
        str: 创建的报告 ID

    Raises:
        Exception: 处理失败时抛出异常
    """
    db: Client = get_db_client()

    try:
        # ============================================
        # Step 1: 创建报告记录（状态为 processing）
        # ============================================
        report_data = {
            "title": filename,
            "filename": filename,
            "status": "processing",
            "file_size": len(file_bytes),
        }

        if user_id:
            report_data["user_id"] = user_id

        # 插入报告记录
        report_result = db.table("reports").insert(report_data).execute()

        if not report_result.data:
            raise Exception("Failed to create report record")

        report_id = report_result.data[0]["id"]
        print(f"[OK] Created report: {report_id}")

        # ============================================
        # Step 2: 提取 PDF 文本内容
        # ============================================
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)

        print(f"[OK] Processing {total_pages} pages...")

        chunks_to_insert = []

        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text")

            # 跳过空页
            if text.strip():
                # 生成文本嵌入向量
                print(f"[INFO] Generating embedding for page {page_num + 1}...")
                embedding = create_embedding(text)

                chunk_data = {
                    "report_id": report_id,
                    "content": text,
                    "page_number": page_num + 1,
                }

                # 如果嵌入生成成功，添加到数据中
                if embedding:
                    chunk_data["embedding"] = embedding
                else:
                    print(f"[WARNING] Failed to generate embedding for page {page_num + 1}, continuing without embedding")

                chunks_to_insert.append(chunk_data)

        doc.close()

        # ============================================
        # Step 3: 批量插入文本块
        # ============================================
        if chunks_to_insert:
            # Supabase 限制单次插入 1000 条，需要分批
            batch_size = 1000
            for i in range(0, len(chunks_to_insert), batch_size):
                batch = chunks_to_insert[i:i + batch_size]
                db.table("report_chunks").insert(batch).execute()

            print(f"[OK] Inserted {len(chunks_to_insert)} chunks")

        # ============================================
        # Step 4: 更新报告状态为 completed
        # ============================================
        db.table("reports").update({
            "status": "completed"
        }).eq("id", report_id).execute()

        print(f"[OK] Report {report_id} processing completed")

        # ============================================
        # Step 5: 生成 AI 摘要
        # ============================================
        print(f"[INFO] Generating AI summary for report {report_id}...")
        generate_summary(report_id)

        return report_id

    except Exception as e:
        # 如果处理失败，更新状态为 failed
        if "report_id" in locals():
            db.table("reports").update({
                "status": "failed"
            }).eq("id", report_id).execute()

        print(f"[ERROR] Error processing PDF: {e}")
        raise
