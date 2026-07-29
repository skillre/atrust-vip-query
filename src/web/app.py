# ============================================================
# Streamlit Web 界面模块
# 提供用户友好的查询界面
# ============================================================

import streamlit as st
import requests
from typing import Optional

from src.config import get_config


def get_api_base_url() -> str:
    """获取 API 基础地址"""
    config = get_config()
    return f"http://localhost:{config.api.port}"


def api_request(
    method: str, 
    path: str, 
    params: Optional[dict] = None
) -> Optional[dict]:
    """
    发送 API 请求
    
    Args:
        method: HTTP 方法
        path: API 路径
        params: 请求参数
    
    Returns:
        响应数据
    """
    url = f"{get_api_base_url()}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=5)
        else:
            response = requests.post(url, json=params, timeout=5)
        
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            return data.get("data")
        else:
            st.error(f"API 错误: {data.get('message')}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error("无法连接到 API 服务，请确保后端已启动")
        return None
    except requests.exceptions.Timeout:
        st.error("请求超时，请稍后重试")
        return None
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


def render_header():
    """渲染页面标题"""
    config = get_config()
    st.set_page_config(
        page_title=config.web.title,
        page_icon="🔍",
        layout="wide"
    )
    st.title("🔍 aTrust 用户虚拟IP查询系统")
    st.markdown("---")


def render_query_section():
    """渲染查询区域"""
    st.subheader("📋 查询用户虚拟IP")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query_name = st.text_input(
            "输入用户名或显示名",
            placeholder="例如: zhangsan 或 张三",
            key="query_name"
        )
    
    with col2:
        source = st.selectbox(
            "数据来源",
            options=["all", "online", "history"],
            format_func=lambda x: {
                "all": "全部",
                "online": "仅在线",
                "history": "仅历史"
            }[x],
            key="source"
        )
    
    if st.button("🔍 查询", type="primary", key="query_btn"):
        if not query_name:
            st.warning("请输入用户名或显示名")
            return
        
        with st.spinner("正在查询..."):
            data = api_request(
                "GET",
                "/api/v1/vip/query",
                params={"name": query_name, "source": source}
            )
        
        if data:
            display_query_result(data)


def display_query_result(data: dict):
    """显示查询结果"""
    st.success("查询成功！")
    
    # 用户信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("用户名", data.get("user_name", "-"))
    with col2:
        st.metric("显示名", data.get("display_name", "-"))
    with col3:
        is_online = data.get("is_online", False)
        st.metric("在线状态", "🟢 在线" if is_online else "🔴 离线")
    
    # 在线虚拟IP
    online_vips = data.get("online_vips", [])
    if online_vips:
        st.subheader("🟢 在线虚拟IP")
        for vip in online_vips:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**虚拟IP:** {vip.get('ip', '-')}")
            with col2:
                st.write(f"**真实IP:** {vip.get('real_ip', '-')}")
    
    # 历史虚拟IP
    history_vip = data.get("history_vip")
    if history_vip:
        st.subheader("📜 最近历史记录")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**虚拟IP:** {history_vip.get('virtual_ip', '-')}")
        with col2:
            st.write(f"**真实IP:** {history_vip.get('real_ip', '-')}")
        with col3:
            st.write(f"**时间:** {history_vip.get('timestamp', '-')}")


def render_reverse_section():
    """渲染反查区域"""
    st.subheader("🔄 按虚拟IP反查用户")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query_ip = st.text_input(
            "输入虚拟IP地址",
            placeholder="例如: 10.10.10.100",
            key="reverse_ip"
        )
    
    with col2:
        limit = st.number_input(
            "返回条数",
            min_value=1,
            max_value=100,
            value=10,
            key="reverse_limit"
        )
    
    if st.button("🔄 反查", type="primary", key="reverse_btn"):
        if not query_ip:
            st.warning("请输入虚拟IP地址")
            return
        
        with st.spinner("正在反查..."):
            data = api_request(
                "GET",
                "/api/v1/vip/reverse",
                params={"ip": query_ip, "limit": limit}
            )
        
        if data:
            display_reverse_result(data)


def display_reverse_result(data: dict):
    """显示反查结果"""
    st.success("反查成功！")
    
    st.info(f"虚拟IP: **{data.get('virtual_ip', '-')}**")
    
    records = data.get("records", [])
    if records:
        st.subheader("关联用户记录")
        
        for i, record in enumerate(records, 1):
            with st.expander(f"记录 {i}: {record.get('user_name', '-')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**用户名:** {record.get('user_name', '-')}")
                    st.write(f"**显示名:** {record.get('display_name', '-')}")
                with col2:
                    st.write(f"**真实IP:** {record.get('real_ip', '-')}")
                    st.write(f"**事件类型:** {record.get('event_type', '-')}")
                st.write(f"**时间:** {record.get('timestamp', '-')}")
    else:
        st.warning("未找到关联记录")


def render_history_section():
    """渲染历史记录区域"""
    st.subheader("📜 查询历史记录")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        history_name = st.text_input(
            "用户名或显示名",
            placeholder="例如: zhangsan",
            key="history_name"
        )
    
    with col2:
        days = st.number_input(
            "查询天数",
            min_value=1,
            max_value=365,
            value=30,
            key="history_days"
        )
    
    with col3:
        page = st.number_input(
            "页码",
            min_value=1,
            value=1,
            key="history_page"
        )
    
    with col4:
        page_size = st.number_input(
            "每页条数",
            min_value=10,
            max_value=100,
            value=20,
            key="history_page_size"
        )
    
    if st.button("📜 查询历史", type="primary", key="history_btn"):
        if not history_name:
            st.warning("请输入用户名或显示名")
            return
        
        with st.spinner("正在查询..."):
            data = api_request(
                "GET",
                "/api/v1/vip/history",
                params={
                    "name": history_name,
                    "days": days,
                    "page": page,
                    "page_size": page_size
                }
            )
        
        if data:
            display_history_result(data)


def display_history_result(data: dict):
    """显示历史记录结果"""
    total = data.get("total", 0)
    page = data.get("page", 1)
    page_size = data.get("page_size", 20)
    records = data.get("records", [])
    
    st.info(f"共找到 **{total}** 条记录，当前第 **{page}** 页")
    
    if records:
        # 使用表格显示
        import pandas as pd
        df = pd.DataFrame(records)
        
        # 重命名列
        column_mapping = {
            "virtual_ip": "虚拟IP",
            "real_ip": "真实IP",
            "event_type": "事件类型",
            "timestamp": "时间"
        }
        df = df.rename(columns=column_mapping)
        
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("未找到历史记录")


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("📊 系统信息")
        
        # 健康检查
        data = api_request("GET", "/api/v1/system/health")
        if data:
            st.success(f"系统状态: {data.get('status', 'unknown')}")
            st.write(f"版本: {data.get('version', '-')}")
            st.write(f"数据库: {data.get('database', '-')}")
            st.write(f"aTrust API: {data.get('atrust_api', '-')}")
            st.write(f"Syslog: {data.get('syslog', '-')}")
        else:
            st.error("无法获取系统状态")
        
        st.markdown("---")
        st.markdown("### 使用说明")
        st.markdown("""
        1. **查询用户**: 输入用户名或显示名
        2. **反查IP**: 输入虚拟IP地址
        3. **历史记录**: 查看用户的历史IP分配
        """)


def main():
    """主函数"""
    render_header()
    render_sidebar()
    
    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["📋 查询虚拟IP", "🔄 反查用户", "📜 历史记录"])
    
    with tab1:
        render_query_section()
    
    with tab2:
        render_reverse_section()
    
    with tab3:
        render_history_section()


if __name__ == "__main__":
    main()
