# Streamlit Web UI Layer

## Responsibility

浏览器端 Streamlit GUI——提供查询、反查、历史、导入、导出五个标签页。纯展示层，通过 HTTP 与 FastAPI 后端通信，不直接访问数据库。

## Dependencies

- **streamlit**: UI 框架（widgets, layout, spinners）
- **requests**: HTTP 客户端（调用 FastAPI 后端）
- **pandas**: DataFrame 构建和 CSV 导出

## Consumers

独立进程，无消费者。通过 `streamlit run src/web/app.py` 启动（端口 8501）。

## Module Structure

```
src/web/
└── app.py    # 690 行，单文件完整 UI（含 CSS + 所有标签页）
```

## API Gateway（唯一后端通信点）

```python
def api_request(method, path, params=None, files=None, timeout=10):
    url = f"{get_api_base_url()}{path}"
    try:
        response = requests.request(method, url, params=params,
                                    files=files, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            return data.get("data")       # 拆信封：只返回 data
        else:
            st.error(f"❌ {data.get('message', '未知错误')}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 无法连接到 API 服务")
        return None
```

所有调用方只需检查 `if data:` 即可，错误已由 gateway 处理。

## Tab Section 生命周期（Input → Validate → Fetch → Display）

```python
def render_query_section():
    st.markdown('<div class="card-header">📋 查询虚拟IP</div>',
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns([4, 2, 1])
    with col1:
        name = st.text_input("用户名", key="query_name",
                             label_visibility="collapsed")
    with col3:
        clicked = st.button("🔍 查询", type="primary", key="query_btn")

    if clicked:
        if not name:
            st.warning("⚠️ 请输入用户名")
            return
        with st.spinner("正在查询..."):
            data = api_request("GET", "/api/v1/vip/query",
                               params={"name": name})
        if data:
            _display_query_result(data)
```

约定：`key=` 必须唯一（防止多标签页 widget ID 冲突），`label_visibility="collapsed"` 隐藏标签，空状态用 `st.info("ℹ️ ...")`。

## Custom CSS 注入

```python
CUSTOM_CSS = """<style>
.card { border-radius: 12px; ... }
.badge-online { background: #dcfce7; color: #166534; }
</style>"""

def render_hero():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)  # 全局注入一次
```

所有 HTML 输出需 `unsafe_allow_html=True`。CSS 类命名：`.card`, `.badge-*`, `.metric-*`, `.hero-*`。

## Architectural Boundaries

- **NO database access**: 只通过 HTTP 调用后端
- **NO shared state with backend**: 无状态进程，每次操作触发新 HTTP 请求
- **NO authentication**: 无 auth 中间件
- **Process independent**: 与 FastAPI 是两个独立进程，需分别启动

<important if="you are adding a new tab to the Streamlit UI">
## Adding a New Tab
1. 在 `app.py` 添加 `render_<name>_section()` 函数
2. 添加 `_display_<name>_result()` 辅助函数（如有数据展示）
3. 在 `main()` 的 `st.tabs([...])` 中添加标签名
4. 在 `with tabN: render_<name>_section()` 中注册
5. 所有 widget 必须有唯一 `key=<tab>_<widget>`
6. API 调用使用 `api_request()`，错误已自动处理
7. 空状态用 `st.info("ℹ️ ...")`
</important>
