# ============================================================
# Streamlit Web 界面模块（v2 — 现代化设计）
# 提供用户友好的查询界面
# ============================================================

import streamlit as st
import requests
import pandas as pd
from typing import Optional
from datetime import datetime

from src.config import get_config


# ======================================================================
# 全局样式
# ======================================================================

CUSTOM_CSS = """
<style>
/* ── 全局字体 & 背景 ── */
.stApp {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
}

/* ── 侧边栏 ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #f1f5f9;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {
    color: #94a3b8;
}

/* ── 标题区 ── */
.hero-title {
    font-size: 2rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.25rem;
}
.hero-subtitle {
    font-size: 1rem;
    color: #64748b;
    margin-top: 0;
}

/* ── 卡片 ── */
.card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}
.card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.card-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── 状态徽章 ── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
}
.badge-online  { background: #dcfce7; color: #166534; }
.badge-offline { background: #fee2e2; color: #991b1b; }
.badge-info    { background: #dbeafe; color: #1e40af; }

/* ── 指标卡片 ── */
.metric-card {
    text-align: center;
    padding: 1rem 0.5rem;
    border-radius: 10px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.2;
}
.metric-label {
    font-size: 0.85rem;
    color: #64748b;
    margin-top: 0.25rem;
}

/* ── 分隔线 ── */
.divider {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 1.5rem 0;
}

/* ── 表格美化 ── */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
}

/* ── 按钮美化 ── */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
</style>
"""


# ======================================================================
# 工具函数
# ======================================================================

def get_api_base_url() -> str:
    config = get_config()
    return f"http://localhost:{config.api.port}"


def api_request(
    method: str,
    path: str,
    params: Optional[dict] = None,
    files: Optional[dict] = None,
    timeout: int = 10
) -> Optional[dict]:
    """发送 API 请求"""
    url = f"{get_api_base_url()}{path}"

    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=timeout)
        elif method == "POST" and files:
            response = requests.post(url, files=files, timeout=timeout)
        else:
            response = requests.post(url, json=params, timeout=timeout)

        response.raise_for_status()
        data = response.json()

        if data.get("code") == 0:
            return data.get("data")
        else:
            st.error(f"❌ {data.get('message', '未知错误')}")
            return None

    except requests.exceptions.ConnectionError:
        st.error("🔌 无法连接到 API 服务，请确保后端已启动")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ 请求超时，请稍后重试")
        return None
    except Exception as e:
        st.error(f"⚠️ 请求失败: {e}")
        return None


def event_type_badge(event_type: str) -> str:
    """事件类型徽章"""
    mapping = {
        "csv_import": ("📥 CSV导入", "badge-info"),
        "syslog_access": ("🌐 访问", "badge-info"),
        "syslog_vip_apply": ("✅ 分配", "badge-online"),
        "syslog_vip_revoke": ("❌ 释放", "badge-offline"),
    }
    label, cls = mapping.get(event_type, (event_type, "badge-info"))
    return f'<span class="badge {cls}">{label}</span>'


# ======================================================================
# 页面渲染
# ======================================================================

def render_hero():
    """渲染页面头部"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-title">🔍 aTrust 用户虚拟IP查询系统</p>'
        '<p class="hero-subtitle">零信任虚拟IP地址管理 · 查询 · 反查 · 导入 · 导出</p>',
        unsafe_allow_html=True
    )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("## ⚙️ 系统状态")

        # 健康检查
        health = api_request("GET", "/api/v1/system/health")
        if health:
            status = health.get("status", "unknown")
            status_color = "🟢" if status == "healthy" else "🟡"
            st.markdown(f"**状态:** {status_color} {status}")
            st.markdown(f"**数据库:** {health.get('database', '-')}")

            syslog = health.get("syslog", {})
            if isinstance(syslog, dict):
                st.markdown(f"**Syslog:** {syslog.get('status', '-')}")
            else:
                st.markdown(f"**Syslog:** {syslog}")

            st.markdown(f"**aTrust API:** {health.get('atrust_api', '-')}")
        else:
            st.error("无法获取系统状态")

        st.markdown("---")

        # 性能统计
        st.markdown("## 📊 性能统计")
        stats = api_request("GET", "/api/v1/system/stats")
        if stats:
            db_stats = stats.get("database", {})
            st.markdown(f"**用户数:** {db_stats.get('user_count', 0):,}")
            st.markdown(f"**记录数:** {db_stats.get('record_count', 0):,}")

            syslog_stats = stats.get("syslog")
            if syslog_stats:
                st.markdown("---")
                st.markdown("#### Syslog 处理")
                st.markdown(f"**已接收:** {syslog_stats.get('received', 0):,}")
                st.markdown(f"**已解析:** {syslog_stats.get('parsed', 0):,}")
                st.markdown(f"**已写入:** {syslog_stats.get('written', 0):,}")
                st.markdown(f"**刷盘次数:** {syslog_stats.get('flushes', 0):,}")

                errors = syslog_stats.get('parse_errors', 0) + syslog_stats.get('write_errors', 0)
                if errors > 0:
                    st.markdown(f"**错误:** {errors:,}")
        else:
            st.info("等待系统启动...")

        st.markdown("---")

        # 使用说明
        with st.expander("📖 使用说明"):
            st.markdown("""
            1. **导入数据** — 上传 aTrust 导出的日志
            2. **查询** — 输入用户名查虚拟IP
            3. **反查** — 输入虚拟IP查用户
            4. **历史** — 查看IP分配历史
            5. **导出** — 下载查询结果 CSV
            """)


# ------------------------------------------------------------------
# Tab 1: 查询虚拟IP
# ------------------------------------------------------------------

def render_query_section():
    """查询用户虚拟IP"""
    st.markdown('<div class="card-header">📋 查询用户虚拟IP</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([4, 2, 1])

    with col1:
        query_name = st.text_input(
            "用户名或显示名",
            placeholder="例如: zhangsan 或 张三",
            label_visibility="collapsed",
            key="query_name"
        )

    with col2:
        source = st.selectbox(
            "数据来源",
            options=["all", "online", "history"],
            format_func=lambda x: {"all": "全部", "online": "仅在线", "history": "仅历史"}[x],
            key="source",
            label_visibility="collapsed"
        )

    with col3:
        query_clicked = st.button("🔍 查询", type="primary", key="query_btn", use_container_width=True)

    if query_clicked:
        if not query_name:
            st.warning("⚠️ 请输入用户名或显示名")
            return

        with st.spinner("正在查询..."):
            data = api_request("GET", "/api/v1/vip/query", params={"name": query_name, "source": source})

        if data:
            _display_query_result(data)


def _display_query_result(data: dict):
    """显示查询结果"""
    user_name = data.get("user_name", "-")
    display_name = data.get("display_name", "-")
    is_online = data.get("is_online", False)

    # 状态行
    status_html = (
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem;">'
        f'<span class="badge badge-online">🟢 在线</span>' if is_online
        else f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem;">'
        f'<span class="badge badge-offline">🔴 离线</span>'
        f'<span style="font-size:1.1rem;font-weight:600;">{user_name}</span>'
        f'<span style="color:#64748b;">({display_name})</span>'
        f'</div>'
    )
    st.markdown(status_html, unsafe_allow_html=True)

    # 在线虚拟IP
    online_vips = data.get("online_vips", [])
    if online_vips:
        st.markdown("##### 🟢 在线虚拟IP")
        for vip in online_vips:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**虚拟IP:** `{vip.get('ip', '-')}`")
            with c2:
                st.markdown(f"**真实IP:** `{vip.get('real_ip', '-')}`")

    # 历史虚拟IP
    history_vip = data.get("history_vip")
    if history_vip:
        st.markdown("##### 📜 最近历史")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**虚拟IP:** `{history_vip.get('virtual_ip', '-')}`")
        with c2:
            st.markdown(f"**真实IP:** `{history_vip.get('real_ip', '-')}`")
        with c3:
            st.markdown(f"**时间:** {history_vip.get('timestamp', '-')}")

    if not online_vips and not history_vip:
        st.info("ℹ️ 未找到虚拟IP记录")


# ------------------------------------------------------------------
# Tab 2: 反查用户
# ------------------------------------------------------------------

def render_reverse_section():
    """按虚拟IP反查用户"""
    st.markdown('<div class="card-header">🔄 按虚拟IP反查用户</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([4, 2, 1])

    with col1:
        query_ip = st.text_input(
            "虚拟IP地址",
            placeholder="例如: 10.10.10.100",
            label_visibility="collapsed",
            key="reverse_ip"
        )

    with col2:
        limit = st.number_input(
            "返回条数",
            min_value=1, max_value=100, value=10,
            key="reverse_limit",
            label_visibility="collapsed"
        )

    with col3:
        reverse_clicked = st.button("🔄 反查", type="primary", key="reverse_btn", use_container_width=True)

    if reverse_clicked:
        if not query_ip:
            st.warning("⚠️ 请输入虚拟IP地址")
            return

        with st.spinner("正在反查..."):
            data = api_request("GET", "/api/v1/vip/reverse", params={"ip": query_ip, "limit": limit})

        if data:
            _display_reverse_result(data)


def _display_reverse_result(data: dict):
    """显示反查结果"""
    vip = data.get("virtual_ip", "-")
    records = data.get("records", [])

    st.markdown(f'**虚拟IP:** `{vip}`　|　**关联记录:** {len(records)} 条')

    if records:
        rows = []
        for r in records:
            rows.append({
                "用户名": r.get("user_name", "-"),
                "显示名": r.get("display_name", "-"),
                "真实IP": r.get("real_ip", "-"),
                "事件类型": r.get("event_type", "-"),
                "时间": r.get("timestamp", "-"),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ 未找到关联记录")


# ------------------------------------------------------------------
# Tab 3: 历史记录
# ------------------------------------------------------------------

def render_history_section():
    """查询历史记录"""
    st.markdown('<div class="card-header">📜 查询历史记录</div>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])

    with col1:
        history_name = st.text_input(
            "用户名或显示名",
            placeholder="例如: zhangsan",
            label_visibility="collapsed",
            key="history_name"
        )

    with col2:
        days = st.number_input("天数", min_value=1, max_value=365, value=30, key="history_days")

    with col3:
        page = st.number_input("页码", min_value=1, value=1, key="history_page")

    with col4:
        page_size = st.number_input("每页", min_value=10, max_value=100, value=20, key="history_page_size")

    with col5:
        history_clicked = st.button("📜 查询", type="primary", key="history_btn", use_container_width=True)

    if history_clicked:
        if not history_name:
            st.warning("⚠️ 请输入用户名或显示名")
            return

        with st.spinner("正在查询..."):
            data = api_request("GET", "/api/v1/vip/history", params={
                "name": history_name, "days": days,
                "page": page, "page_size": page_size
            })

        if data:
            _display_history_result(data, history_name, days)


def _display_history_result(data: dict, name: str, days: int):
    """显示历史记录结果"""
    total = data.get("total", 0)
    page = data.get("page", 1)
    page_size = data.get("page_size", 20)
    records = data.get("records", [])

    # 统计行
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total:,}</div>'
                     f'<div class="metric-label">总记录数</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{page}</div>'
                     f'<div class="metric-label">当前页</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{days}</div>'
                     f'<div class="metric-label">查询天数</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(records)}</div>'
                     f'<div class="metric-label">本页条数</div></div>', unsafe_allow_html=True)

    if records:
        df = pd.DataFrame(records)
        df = df.rename(columns={
            "virtual_ip": "虚拟IP",
            "real_ip": "真实IP",
            "event_type": "事件类型",
            "timestamp": "时间"
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 导出按钮
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 导出 CSV",
            data=csv,
            file_name=f"history_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("ℹ️ 未找到历史记录")


# ------------------------------------------------------------------
# Tab 4: 导入数据
# ------------------------------------------------------------------

def render_import_section():
    """导入日志数据"""
    st.markdown('<div class="card-header">📥 导入日志数据</div>', unsafe_allow_html=True)

    st.info("📤 上传 aTrust 导出的 CSV 或 Excel 访问日志文件，系统自动提取用户名、虚拟IP等关键信息。")

    uploaded_file = st.file_uploader(
        "选择日志文件",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed",
        key="log_file"
    )

    if uploaded_file is not None:
        # 文件信息
        file_size_kb = uploaded_file.size / 1024
        if file_size_kb > 1024:
            size_str = f"{file_size_kb / 1024:.1f} MB"
        else:
            size_str = f"{file_size_kb:.1f} KB"

        st.markdown(f"📄 **{uploaded_file.name}** ({size_str})")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("👁️ 预览数据", type="secondary", key="preview_btn", use_container_width=True):
                with st.spinner("正在解析文件..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    result = api_request("POST", "/api/v1/import/preview", files=files, timeout=30)

                    if result:
                        st.success(f"✅ 解析成功！共 {result.get('total_rows', 0):,} 行数据")

                        columns = result.get("columns", [])
                        if columns:
                            st.markdown(f"**检测到 {len(columns)} 列:**")
                            st.code(", ".join(columns[:15]) + ("..." if len(columns) > 15 else ""))

                        preview = result.get("preview", [])
                        if preview:
                            st.markdown("**前 5 行预览:**")
                            st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

        with col2:
            if st.button("📥 开始导入", type="primary", key="import_btn", use_container_width=True):
                with st.spinner("⏳ 正在导入数据，大文件可能需要几分钟..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    result = api_request("POST", "/api/v1/import/upload", files=files, timeout=300)

                    if result:
                        st.success(f"✅ {result.get('message', '导入成功')}")

                        # 导入统计
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric("总行数", f"{result.get('total_rows', 0):,}")
                        with c2:
                            st.metric("成功导入", f"{result.get('imported', 0):,}")
                        with c3:
                            st.metric("跳过", f"{result.get('skipped', 0):,}")
                        with c4:
                            err_count = result.get('errors', 0)
                            st.metric("错误", f"{err_count:,}", delta=None if err_count == 0 else f"-{err_count}")

                        if err_count > 0:
                            st.warning(f"⚠️ 有 {err_count} 行数据处理出错")

    # 使用说明
    with st.expander("📖 导入说明", expanded=False):
        st.markdown("""
        | 步骤 | 操作 |
        |------|------|
        | 1 | 从 aTrust 控制台导出访问日志（CSV 或 Excel） |
        | 2 | 上传到本系统 |
        | 3 | 自动提取 **用户名、虚拟IP、真实IP** 等关键信息 |
        | 4 | 导入后即可使用查询、反查、历史记录等功能 |

        💡 **提示:** 支持多次导入，重复数据会自动更新。建议定期导入以保持数据最新。
        """)


# ------------------------------------------------------------------
# Tab 5: 数据导出
# ------------------------------------------------------------------

def render_export_section():
    """数据导出"""
    st.markdown('<div class="card-header">📤 数据导出</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3, 2, 2])

    with col1:
        export_name = st.text_input(
            "用户名筛选（可选）",
            placeholder="留空导出全部",
            label_visibility="collapsed",
            key="export_name"
        )

    with col2:
        export_days = st.number_input("导出天数", min_value=1, max_value=365, value=30, key="export_days")

    with col3:
        export_type = st.selectbox(
            "事件类型",
            options=[None, "csv_import", "syslog_access", "syslog_vip_apply", "syslog_vip_revoke"],
            format_func=lambda x: {
                None: "全部类型",
                "csv_import": "📥 CSV导入",
                "syslog_access": "🌐 访问",
                "syslog_vip_apply": "✅ 分配",
                "syslog_vip_revoke": "❌ 释放"
            }.get(x, x),
            key="export_type",
            label_visibility="collapsed"
        )

    # 预览按钮
    if st.button("👁️ 预览数据", type="secondary", key="export_preview_btn", use_container_width=True):
        with st.spinner("正在查询..."):
            db_stats = api_request("GET", "/api/v1/system/stats")
            # 通过 API 获取导出数据预览
            url = f"{get_api_base_url()}/api/v1/vip/history"
            params = {"name": export_name or "*", "days": export_days, "page": 1, "page_size": 100}
            data = api_request("GET", "/api/v1/vip/history", params=params)

            if data and data.get("records"):
                records = data["records"]
                df = pd.DataFrame(records)
                df = df.rename(columns={
                    "virtual_ip": "虚拟IP", "real_ip": "真实IP",
                    "event_type": "事件类型", "timestamp": "时间"
                })
                st.markdown(f"**预览（前 {len(records)} 条）:**")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ 未找到符合条件的数据")

    # 下载按钮
    export_url = f"{get_api_base_url()}/api/v1/export/csv"
    export_params = {"days": export_days}
    if export_name:
        export_params["name"] = export_name
    if export_type:
        export_params["event_type"] = export_type

    # 构建完整下载 URL
    query_str = "&".join(f"{k}={v}" for k, v in export_params.items())
    download_url = f"{export_url}?{query_str}"

    st.markdown(f'<a href="{download_url}" target="_blank">'
                f'<button style="background:#2563eb;color:white;padding:0.5rem 1.5rem;'
                f'border:none;border-radius:8px;font-weight:600;cursor:pointer;'
                f'font-size:1rem;">📥 下载 CSV 文件</button></a>',
                unsafe_allow_html=True)

    st.caption("💡 点击按钮将通过浏览器下载 CSV 文件")


# ======================================================================
# 主函数
# ======================================================================

def main():
    """主函数"""
    config = get_config()
    st.set_page_config(
        page_title=config.web.title,
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    render_hero()
    render_sidebar()

    # 标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 查询虚拟IP",
        "🔄 反查用户",
        "📜 历史记录",
        "📥 导入数据",
        "📤 数据导出"
    ])

    with tab1:
        render_query_section()
    with tab2:
        render_reverse_section()
    with tab3:
        render_history_section()
    with tab4:
        render_import_section()
    with tab5:
        render_export_section()


if __name__ == "__main__":
    main()
