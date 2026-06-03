"""评审文件上传与解析服务

处理文件上传、格式解析（PDF/Word/TXT/压缩包）、文本提取，
并将解析结果持久化到 eval_material 表。

依赖（可选导入，缺失时对应格式返回空文本）：
  - pypdf:         PDF 解析
  - python-docx:   .docx 解析
  - openpyxl:      .xlsx 解析（已在 requirements.txt 中）
  - rarfile:       .rar 解压回退方案
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.env import UploadConfig
from module_eval.entity.do.eval_do import EvalMaterial
from utils.log_util import logger

# ---------------------------------------------------------------------------
# 可选依赖（按需安装，缺失时对应格式返回空文本）
# ---------------------------------------------------------------------------

try:
    from pypdf import PdfReader as _PdfReader

    HAS_PYPDF = True
except ImportError:
    _PdfReader = None  # type: ignore[assignment]
    HAS_PYPDF = False

try:
    from docx import Document as _DocxDocument

    HAS_DOCX = True
except ImportError:
    _DocxDocument = None  # type: ignore[assignment]
    HAS_DOCX = False

try:
    from openpyxl import load_workbook as _load_workbook

    HAS_OPENPYXL = True
except ImportError:
    _load_workbook = None  # type: ignore[assignment]
    HAS_OPENPYXL = False

try:
    import rarfile as _rarfile

    HAS_RARFILE = True
except ImportError:
    _rarfile = None  # type: ignore[assignment]
    HAS_RARFILE = False

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: set[str] = {ext.lower() for ext in UploadConfig.DEFAULT_ALLOWED_EXTENSION}

PARSEABLE_EXTENSIONS: set[str] = {
    ".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".xls",
}

ARCHIVE_EXTENSIONS: set[str] = {".zip", ".rar"}

# ---------------------------------------------------------------------------
# 文本质量检测
# ---------------------------------------------------------------------------


def _is_garbled_text(text: str) -> bool:
    """检测文本是否为乱码（从 os-bid-eval-web material_aggregator 移植）。

    PDF 文字提取引擎有时输出错误的编码残留（西里尔/阿拉伯等非预期字符），
    通过合法字符占比判断文本是否可用。
    """
    if not text or not text.strip():
        return True
    meaningful = [c for c in text if not c.isspace()]
    if not meaningful:
        return True
    total = len(meaningful)

    # 合法字符分类
    cjk = sum(1 for c in meaningful if "\u4e00" <= c <= "\u9fff" or "\u3400" <= c <= "\u4dbf")
    fullwidth = sum(1 for c in meaningful if "\uff00" <= c <= "\ufeff")
    cjk_punct = sum(1 for c in meaningful if "\u3000" <= c <= "\u303f")
    ascii_char = sum(1 for c in meaningful if c.isascii())

    # 乱码标记字符集
    garbled = sum(
        1
        for c in meaningful
        if ("\u0400" <= c <= "\u04ff")       # Cyrillic
        or ("\u0500" <= c <= "\u052f")       # Cyrillic Supplement
        or ("\u0600" <= c <= "\u06ff")       # Arabic
        or ("\u0750" <= c <= "\u077f")       # Arabic Supplement
        or ("\u0590" <= c <= "\u05ff")       # Hebrew
        or ("\u0e00" <= c <= "\u0e7f")       # Thai
        or ("\u1780" <= c <= "\u17ff")       # Khmer
        or ("\u0370" <= c <= "\u03ff")       # Greek
        or ("\u02b0" <= c <= "\u02ff")       # Spacing Modifier Letters
        or c == "\ufffd"                      # Replacement Character
    )

    if garbled / total > 0.03:
        return True

    legitimate = cjk + fullwidth + cjk_punct + ascii_char
    if total > 100 and legitimate / total < 0.5:
        return True

    return False


# ---------------------------------------------------------------------------
# 单文件读取
# ---------------------------------------------------------------------------


def _read_txt(fp: Path) -> str:
    """读取纯文本 / Markdown 文件。"""
    try:
        return fp.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _read_pdf(fp: Path) -> str:
    """使用 pypdf 读取 PDF 文本。"""
    if not HAS_PYPDF:
        logger.warning("pypdf 未安装，无法解析 PDF: %s", fp.name)
        return ""
    try:
        reader = _PdfReader(str(fp))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        text = "\n".join(pages)
        if text.strip() and not _is_garbled_text(text):
            return text
        logger.warning("PDF 文本提取结果为乱码，跳过: %s", fp.name)
        return ""
    except Exception as e:
        logger.warning("PDF 解析失败: %s — %s", fp.name, e)
        return ""


def _read_docx(fp: Path) -> str:
    """使用 python-docx 读取 .docx 文本（含段落 + 表格）。"""
    if not HAS_DOCX:
        logger.warning("python-docx 未安装，无法解析 DOCX: %s", fp.name)
        return ""
    try:
        doc = _DocxDocument(str(fp))
        paragraphs = [p.text for p in doc.paragraphs]
        # 表格内容
        table_lines: list[str] = []
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_lines.append(" | ".join(cells))
        all_lines = paragraphs + table_lines
        return "\n".join(all_lines)
    except Exception as e:
        logger.warning("DOCX 解析失败: %s — %s", fp.name, e)
        return ""


def _read_xlsx(fp: Path) -> str:
    """使用 openpyxl 读取 .xlsx 文本。

    遍历所有工作表，提取每个非空单元格的文本，以制表符分隔列、换行分隔行。
    """
    if not HAS_OPENPYXL:
        logger.warning("openpyxl 未安装，无法解析 XLSX: %s", fp.name)
        return ""
    try:
        wb = _load_workbook(str(fp), read_only=True, data_only=True)
        lines: list[str] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            sheet_lines: list[str] = []
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                line = "\t".join(cells)
                if line.strip():
                    sheet_lines.append(line)
            if sheet_lines:
                lines.append(f"【工作表: {sheet_name}】")
                lines.extend(sheet_lines)
        wb.close()
        return "\n".join(lines)
    except Exception as e:
        logger.warning("XLSX 解析失败: %s — %s", fp.name, e)
        return ""


# ---------------------------------------------------------------------------
# 压缩包处理
# ---------------------------------------------------------------------------


def _extract_zip_text(fp: Path) -> str:
    """解压 ZIP 并递归解析内部文件。"""
    tmp_dir = tempfile.mkdtemp(prefix="eval_zip_")
    try:
        with zipfile.ZipFile(fp, "r") as zf:
            zf.extractall(tmp_dir)
        return _scan_directory(Path(tmp_dir), fp.name)
    except Exception as e:
        logger.warning("ZIP 解压失败: %s — %s", fp.name, e)
        return ""
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _extract_rar_text(fp: Path) -> str:
    """解压 RAR 并递归解析内部文件。

    策略：系统命令 unrar/UnRAR（支持 RAR5） > rarfile 库回退。
    """
    tmp_dir = tempfile.mkdtemp(prefix="eval_rar_")
    extracted = False
    try:
        # 1) 系统 unrar / UnRAR 命令
        for cmd_name in ["unrar", "UnRAR"]:
            cmd_path = shutil.which(cmd_name)
            if not cmd_path and cmd_name == "UnRAR":
                for guess in [
                    r"C:\Program Files\WinRAR\UnRAR.exe",
                    r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
                ]:
                    if Path(guess).exists():
                        cmd_path = guess
                        break
            if cmd_path:
                try:
                    result = subprocess.run(
                        [cmd_path, "x", "-o+", str(fp), str(tmp_dir) + os.sep],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if result.returncode == 0:
                        extracted = True
                        break
                except Exception:
                    continue

        # 2) rarfile 库回退
        if not extracted and HAS_RARFILE:
            try:
                with _rarfile.RarFile(str(fp), "r") as rf:
                    rf.extractall(str(tmp_dir))
                extracted = True
            except Exception:
                pass

        if not extracted:
            logger.warning("RAR 解压失败（请安装 WinRAR 或 rarfile 库）: %s", fp.name)
            return ""

        return _scan_directory(Path(tmp_dir), fp.name)
    except Exception as e:
        logger.warning("RAR 处理异常: %s — %s", fp.name, e)
        return ""
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _scan_directory(directory: Path, archive_name: str = "") -> str:
    """递归扫描目录下的可解析文件，拼接所有文本。

    Args:
        directory: 要扫描的目录
        archive_name: 归档文件名（可选，用于输出中标记来源）

    Returns:
        所有可解析文件的拼接文本，每条带来源标记
    """
    chunks: list[str] = []
    for fp in sorted(directory.rglob("*")):
        if not fp.is_file():
            continue
        ext = fp.suffix.lower()
        if ext in ARCHIVE_EXTENSIONS:
            # 嵌套压缩包: 跳过，不递归解压
            continue
        if ext not in PARSEABLE_EXTENSIONS:
            continue
        text = extract_text(str(fp))
        if text.strip():
            rel = fp.relative_to(directory)
            label = f"{archive_name}/{rel}" if archive_name else str(rel)
            chunks.append(f"【{label}】\n{text}")
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# 公开函数：extract_text（供外部直接调用）
# ---------------------------------------------------------------------------


def extract_text(file_path: str) -> str:
    """从文件提取文本内容。

    支持格式：
      - .pdf            — pypdf
      - .docx / .doc    — python-docx
      - .xlsx / .xls    — openpyxl
      - .txt / .md      — UTF-8 直接读取
      - .zip            — 解压后递归解析内部文件
      - .rar            — 解压后递归解析内部文件

    其他格式返回空字符串。
    """
    fp = Path(file_path)
    if not fp.is_file():
        logger.warning("文件不存在: %s", file_path)
        return ""

    ext = fp.suffix.lower()

    if ext in {".txt", ".md"}:
        return _read_txt(fp)

    if ext == ".pdf":
        return _read_pdf(fp)

    if ext in {".docx", ".doc"}:
        return _read_docx(fp)

    if ext in {".xlsx", ".xls"}:
        return _read_xlsx(fp)

    if ext == ".zip":
        return _extract_zip_text(fp)

    if ext == ".rar":
        return _extract_rar_text(fp)

    logger.debug("不支持的格式: %s", ext)
    return ""


# ---------------------------------------------------------------------------
# 主服务类
# ---------------------------------------------------------------------------


class EvalFileService:
    """评审文件上传与解析服务"""

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @classmethod
    def _get_project_upload_dir(cls, project_id: int) -> Path:
        """获取项目的上传文件根目录（不存在时自动创建）。

        目录结构: {UploadConfig.UPLOAD_PATH}/eval_files/{project_id}/
        """
        upload_dir = Path(UploadConfig.UPLOAD_PATH) / "eval_files" / str(project_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    # ------------------------------------------------------------------
    # 上传并解析
    # ------------------------------------------------------------------

    @classmethod
    async def upload_and_parse(
        cls, file: UploadFile, project_id: int, query_db: AsyncSession, category: str = ''
    ) -> dict[str, Any]:
        """上传文件并解析，记录到 eval_material 表。

        Args:
            file: FastAPI 上传文件对象
            project_id: 所属项目 ID
            query_db: 数据库会话
            category: 文件分类（请示函/招标文件/可研报告/法律意见/其他）

        Returns:
            dict: {
                "material_id": int,
                "file_name": str,
                "file_path": str,
                "file_size": int,
                "file_type": str,
                "category": str,
                "parse_status": Literal["done", "error"],
            }

        Raises:
            ValueError: 文件类型不被 allowed_extensions 允许
        """
        original_name = file.filename or "unknown"
        ext = Path(original_name).suffix.lower()

        # 1. 校验扩展名
        if ext.lstrip(".") not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型 [{ext}]，允许: {sorted(ALLOWED_EXTENSIONS)}")

        # 2. 安全写入磁盘（带时间戳 + 随机数避免覆盖）
        project_dir = cls._get_project_upload_dir(project_id)
        stem = Path(original_name).stem
        safe_name = f"{stem}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}{ext}"
        dest_path = project_dir / safe_name

        content = await file.read()
        dest_path.write_bytes(content)
        file_size = len(content)

        # 3. 解析文本
        try:
            text_content = extract_text(str(dest_path))
        except Exception as e:
            text_content = ""
            logger.error("文件解析异常: %s — %s", original_name, e)

        parse_status = "done" if text_content.strip() else "error"
        if parse_status == "error":
            logger.warning("文件解析结果为空: %s", original_name)

        # 4. 持久化到 eval_material
        material = EvalMaterial(
            project_id=project_id,
            file_name=original_name,
            file_path=str(dest_path),
            file_size=file_size,
            file_type=ext.lstrip("."),
            category=category or '其他',
            text_content=text_content,
            parse_status=parse_status,
        )

        try:
            query_db.add(material)
            await query_db.flush()
        except Exception:
            await query_db.rollback()
            # 清理已写入的磁盘文件
            try:
                dest_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

        logger.info(
            "文件上传解析完成 | project=%s file=%s size=%s type=%s status=%s",
            project_id, original_name, file_size, ext, parse_status,
        )

        return {
            "material_id": material.material_id,
            "file_name": original_name,
            "file_path": str(dest_path),
            "file_size": file_size,
            "file_type": ext.lstrip("."),
            "category": category,
            "parse_status": parse_status,
        }

    # ------------------------------------------------------------------
    # 文本提取（委托给模块函数）
    # ------------------------------------------------------------------

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """从文件提取文本内容。

        等价于模块级 :func:`extract_text`，作为类方法暴露以便统一调用风格。
        """
        return extract_text(file_path)

    # ------------------------------------------------------------------
    # 聚合材料
    # ------------------------------------------------------------------

    @classmethod
    async def aggregate_materials(cls, project_id: int, query_db: AsyncSession) -> str:
        """聚合项目所有已解析材料的文本内容。

        从 eval_material 表读取当前项目下 parse_status = 'done' 的记录，
        按上传时间升序排列，拼接为带文件名标记的统一文本。
        供后续 LLM 评审流程作为材料上下文输入。

        Args:
            project_id: 项目 ID
            query_db: 数据库会话

        Returns:
            所有材料的拼接文本，每条以 "【文件名】" 开头；
            无材料时返回空字符串。
        """
        result = await query_db.execute(
            select(EvalMaterial)
            .where(
                EvalMaterial.project_id == project_id,
                EvalMaterial.parse_status == "done",
            )
            .order_by(EvalMaterial.create_time.asc().nullsfirst())
        )
        materials = list(result.scalars().all())

        if not materials:
            logger.info("项目 %s 无已解析材料", project_id)
            return ""

        chunks: list[str] = []
        total_chars = 0
        for mat in materials:
            header = f"【{mat.file_name}】"
            text = (mat.text_content or "").strip()
            if text:
                chunks.append(f"{header}\n{text}")
                total_chars += len(text)

        combined = "\n\n".join(chunks)

        logger.info(
            "材料聚合完成 | project=%s files=%s total_chars=%s",
            project_id, len(materials), total_chars,
        )
        return combined
