"""
OCR Service - PDF Content Extraction

使用 PyMuPDF (fitz) 提取 PDF 文本内容并存储到 Supabase
"""
from app.core.db import get_db_client
from utils.db_helper import safe_insert


def process_pdf(
    file_bytes: bytes,
    filename: str,
    user_id: str | None = None
) -> str:
    """
    处理 PDF 文件：提取文本并存储到数据库
    """
    # 创建报告记录（状态为 processing）
    report_data = {
        "title": filename,
        "filename": filename,
        "status": "processing",
        "file_size": len(file_bytes),
    }

    if user_id:
        report_data["user_id"] = user_id

    # 使用辅助函数插入报告记录
    report_result = safe_insert("reports", report_data)

    if not report_result:
        raise Exception("Failed to create report record")

    report_id = report_result[0]["id"]
    print(f"[OK] Created report: {report_id}")

    return report_result
