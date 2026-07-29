# ============================================================
# 日志文件导入模块（高性能版）
# 支持导入 aTrust 导出的 CSV/Excel 访问日志
# 分块批量处理，适用于 6000w+ 行大文件
# ============================================================

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from loguru import logger

from src.config import get_config
from src.storage.models import UserInfo, VipRecord
from src.storage.database import get_database


# CSV 列名映射（aTrust 导出的列名 -> 系统内部字段）
COLUMN_MAPPING = {
    # 用户信息
    "用户名": "user_name",
    "显示名": "display_name",
    "所属组织架构": "org_path",
    "所属用户目录": "user_directory",
    "手机号码": "phone",
    "电子邮箱": "email",

    # 虚拟IP信息
    "虚拟IP": "virtual_ip",
    "客户端源IP": "client_ip",
    "代理网关源IP": "gateway_ip",

    # 时间
    "时间": "timestamp",

    # 终端信息
    "终端名称": "terminal_name",
    "品牌型号": "brand_model",
    "操作系统": "os",
    "MAC地址": "mac_address",
    "终端ID": "terminal_id",

    # 访问信息
    "操作类型": "op_type",
    "操作子类型": "op_subtype",
    "结果": "result",
    "访问协议": "protocol",
    "访问地址": "access_url",
    "应用名称": "app_name",

    # 位置信息
    "IP归属国家": "ip_country",
    "IP归属城市": "ip_city",
    "登录IP": "login_ip",
}

# 标记为空值的字符串
EMPTY_VALUES = {" -", "-", "—", "N/A", "n/a", "", "None", "null"}


def _clean_value(value: Optional[str]) -> Optional[str]:
    """清洗字段值 - 处理 aTrust CSV 导出的特殊格式"""
    if value is None:
        return None

    value = str(value)

    # 去除首尾空白、tab、换行
    value = value.strip().strip("\t").strip("\n").strip("\r")

    # 去除外层引号包裹
    for _ in range(5):
        changed = False
        if value.startswith('"""') and value.endswith('"""'):
            value = value[3:-3]
            changed = True
        elif value.startswith("'''") and value.endswith("'''"):
            value = value[3:-3]
            changed = True
        elif value.startswith('"') and value.endswith('"') and len(value) > 1:
            value = value[1:-1]
            changed = True
        elif value.startswith("'") and value.endswith("'") and len(value) > 1:
            value = value[1:-1]
            changed = True
        if not changed:
            break

    value = value.strip().strip("\t").strip()

    if value in EMPTY_VALUES:
        return None

    return value if value else None


def _parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """解析时间戳"""
    if not ts_str:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(ts_str.strip(), fmt)
        except ValueError:
            continue

    logger.warning(f"无法解析时间戳: {ts_str}")
    return None


def _parse_csv_content(content: str) -> List[Dict[str, str]]:
    """解析 CSV 内容"""
    rows = []

    reader = csv.reader(
        io.StringIO(content),
        quotechar='"',
        doublequote=True
    )

    headers = None

    for row_num, row in enumerate(reader, 1):
        if not row or all(cell.strip() == "" for cell in row):
            continue

        if headers is None:
            headers = [_clean_value(h) or f"col_{i}" for i, h in enumerate(row)]
            continue

        if len(row) == len(headers):
            row_dict = {}
            for i, value in enumerate(row):
                row_dict[headers[i]] = value
            rows.append(row_dict)
        else:
            logger.debug(f"第 {row_num} 行列数不匹配，跳过: {len(row)} vs {len(headers)}")

    return rows


class FileImporter:
    """
    日志文件导入器（高性能版）

    特性：
    - 分块批量处理：将大文件拆分为小批次写入数据库
    - 单事务提交：每批数据在单个事务中提交
    - 进度反馈：返回详细的导入统计
    """

    def __init__(self):
        self.db = get_database()
        config = get_config()
        self.batch_size = config.database.batch_size

    def import_csv(self, content: str, filename: str = "upload.csv") -> Dict:
        """
        导入 CSV 文件（分块批量处理）

        Args:
            content: CSV 文件内容（字符串）
            filename: 文件名（用于日志）

        Returns:
            导入结果统计
        """
        logger.info(f"开始导入 CSV 文件: {filename}")

        # 解析 CSV
        rows = _parse_csv_content(content)

        if not rows:
            return {
                "success": False,
                "message": "CSV 文件为空或格式无法解析",
                "total_rows": 0,
                "imported": 0,
                "skipped": 0,
                "errors": 0
            }

        logger.info(f"CSV 解析完成，共 {len(rows)} 行数据")

        # 统计
        stats = {
            "success": True,
            "message": "",
            "total_rows": len(rows),
            "imported": 0,
            "skipped": 0,
            "errors": 0,
            "users_found": 0,
            "vip_records": 0,
        }

        # 分块处理
        total_chunks = (len(rows) + self.batch_size - 1) // self.batch_size

        for chunk_idx in range(total_chunks):
            start = chunk_idx * self.batch_size
            end = min(start + self.batch_size, len(rows))
            chunk = rows[start:end]

            chunk_users: List[UserInfo] = []
            chunk_records: List[VipRecord] = []
            chunk_errors = 0

            for i, row in enumerate(chunk):
                try:
                    user_info, vip_record = self._extract_from_row(row)
                    if user_info:
                        chunk_users.append(user_info)
                    if vip_record:
                        chunk_records.append(vip_record)
                        stats["imported"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception as e:
                    chunk_errors += 1
                    stats["errors"] += 1
                    if stats["errors"] <= 5:
                        logger.error(f"处理第 {start + i + 1} 行失败: {e}")

            # 批量写入
            if chunk_users or chunk_records:
                result = self.db.batch_process(chunk_users, chunk_records)
                stats["users_found"] += result["users_ok"]
                stats["vip_records"] += result["records_ok"]

            # 进度日志（每 10% 输出一次）
            progress = (chunk_idx + 1) / total_chunks
            if total_chunks > 1 and (chunk_idx + 1) % max(1, total_chunks // 10) == 0:
                logger.info(f"导入进度: {progress:.0%} ({end}/{len(rows)} 行)")

        stats["message"] = (
            f"导入完成：共 {stats['total_rows']} 行，"
            f"成功 {stats['imported']}，跳过 {stats['skipped']}，"
            f"错误 {stats['errors']}"
        )

        logger.info(stats["message"])
        return stats

    def import_file(self, file_content: bytes, filename: str) -> Dict:
        """
        导入文件（自动识别格式）

        Args:
            file_content: 文件二进制内容
            filename: 文件名

        Returns:
            导入结果统计
        """
        suffix = Path(filename).suffix.lower()

        if suffix == ".csv":
            for encoding in ["utf-8", "gbk", "gb2312", "utf-8-sig"]:
                try:
                    content = file_content.decode(encoding)
                    return self.import_csv(content, filename)
                except UnicodeDecodeError:
                    continue

            return {
                "success": False,
                "message": "无法识别文件编码，请尝试转为 UTF-8 编码",
                "total_rows": 0,
                "imported": 0,
                "skipped": 0,
                "errors": 0
            }

        elif suffix in (".xlsx", ".xls"):
            return self._import_excel(file_content, filename)

        else:
            return {
                "success": False,
                "message": f"不支持的文件格式: {suffix}，请上传 CSV 或 Excel 文件",
                "total_rows": 0,
                "imported": 0,
                "skipped": 0,
                "errors": 0
            }

    def _import_excel(self, file_content: bytes, filename: str) -> Dict:
        """导入 Excel 文件"""
        try:
            import pandas as pd
            import io

            df = pd.read_excel(io.BytesIO(file_content))
            csv_content = df.to_csv(index=False)
            return self.import_csv(csv_content, filename)

        except ImportError:
            return {
                "success": False,
                "message": "Excel 导入需要安装 pandas 和 openpyxl，请上传 CSV 格式",
                "total_rows": 0,
                "imported": 0,
                "skipped": 0,
                "errors": 0
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Excel 解析失败: {e}",
                "total_rows": 0,
                "imported": 0,
                "skipped": 0,
                "errors": 0
            }

    def _extract_from_row(self, row: Dict[str, str]) -> Tuple[Optional[UserInfo], Optional[VipRecord]]:
        """
        从单行数据中提取用户信息和虚拟IP记录

        Returns:
            (user_info, vip_record) — 任一可能为 None
        """
        user_name = _clean_value(row.get("用户名"))
        if not user_name:
            return None, None

        virtual_ip = _clean_value(row.get("虚拟IP"))
        timestamp = _parse_timestamp(_clean_value(row.get("时间")))
        client_ip = _clean_value(row.get("客户端源IP"))

        if not virtual_ip and not client_ip:
            return None, None

        user_info = UserInfo(
            user_name=user_name,
            display_name=_clean_value(row.get("显示名")),
            phone=_clean_value(row.get("手机号码")),
            email=_clean_value(row.get("电子邮箱")),
            directory_name=_clean_value(row.get("所属用户目录")),
            group_path=_clean_value(row.get("所属组织架构"))
        )

        vip_record = None
        if virtual_ip:
            vip_record = VipRecord(
                user_name=user_name,
                virtual_ip=virtual_ip,
                real_ip=client_ip,
                event_type="csv_import",
                timestamp=timestamp or datetime.now()
            )

        return user_info, vip_record

    def get_import_preview(self, content: str, max_rows: int = 5) -> Dict:
        """预览 CSV 文件（不导入，只解析前几行）"""
        rows = _parse_csv_content(content)

        if not rows:
            return {"success": False, "message": "无法解析文件"}

        preview_rows = []
        for row in rows[:max_rows]:
            preview_rows.append({
                "用户名": _clean_value(row.get("用户名")) or "-",
                "显示名": _clean_value(row.get("显示名")) or "-",
                "虚拟IP": _clean_value(row.get("虚拟IP")) or "-",
                "客户端源IP": _clean_value(row.get("客户端源IP")) or "-",
                "时间": _clean_value(row.get("时间")) or "-",
            })

        return {
            "success": True,
            "total_rows": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "preview": preview_rows
        }


# 全局导入器实例
_importer: Optional[FileImporter] = None
_importer_lock = __import__("threading").Lock()


def get_file_importer() -> FileImporter:
    """获取全局文件导入器实例"""
    global _importer
    if _importer is None:
        with _importer_lock:
            if _importer is None:
                _importer = FileImporter()
    return _importer
