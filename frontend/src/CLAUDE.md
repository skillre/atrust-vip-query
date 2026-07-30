# React SPA Frontend

## Responsibility

浏览器端 React 单页应用——提供查询、反查、历史、导入、导出五个标签页。通过 `fetch()` 与 FastAPI 后端通信，不直接访问数据库。

## Dependencies

- **react**: UI 框架（useState, useEffect, useRef）
- **react-dom**: DOM 渲染（createRoot）
- **Vite**: 构建工具 + 开发代理（`/api` → localhost:8000）

## Consumers

- Vite 开发服务器（端口 3000）
- FastAPI 静态文件服务（生产环境，React 构建产物挂载到根路径）

## Module Structure

```
frontend/src/
├── main.jsx          # 入口：createRoot 挂载 App
├── App.jsx           # 根组件：状态管理 + 标签页路由
├── config.js         # API_BASE = '/api/v1'
├── index.css         # 全局样式（Apple Design Token）
└── components/       # 10 个 UI 组件（全 function component）
    ├── HeroSearch.jsx    # 首页搜索栏
    ├── QueryPanel.jsx    # 正向查询
    ├── ReversePanel.jsx  # 反向查询
    ├── HistoryPanel.jsx  # 历史记录
    ├── ImportPanel.jsx   # 文件导入（拖拽上传）
    ├── ExportPanel.jsx   # 数据导出
    ├── StatsRow.jsx      # 统计概览（4 列网格）
    ├── Nav.jsx           # 导航栏 + 系统状态
    ├── Footer.jsx        # 页脚
    └── Toast.jsx         # 自动消失通知（3 秒）
```

## App Shell — 集中状态 + 标签页路由

```jsx
export default function App() {
  const [activeTab, setActiveTab] = useState('query')
  const [queryInput, setQueryInput] = useState('')

  function handleSearch(input, type) {
    setQueryInput(input)
    setActiveTab(type === 'ip' ? 'reverse' : 'query')
  }

  return (
    <>
      <Nav activeTab={activeTab} onTabChange={setActiveTab} />
      <HeroSearch onSearch={handleSearch} />
      {activeTab === 'query'   && <QueryPanel queryInput={queryInput} />}
      {activeTab === 'reverse' && <ReversePanel queryInput={queryInput} />}
      {activeTab === 'history' && <HistoryPanel />}
      {activeTab === 'import'  && <ImportPanel onImportComplete={...} />}
      {activeTab === 'export'  && <ExportPanel />}
      <Toast message={toast.message} onClose={...} />
    </>
  )
}
```

无路由库——`activeTab` 字符串驱动 UI 切换。面板切换时完全卸载（状态重置）。

## Self-Contained Panel — 三态渲染

```jsx
export default function QueryPanel({ queryInput }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function performSearch(param) {
    setLoading(true); setError(null); setResult(null)
    try {
      const resp = await fetch(
        `${API_BASE}/vip/query?name=${encodeURIComponent(param)}`
      )
      const data = await resp.json()
      data.code === 0 && data.data
        ? setResult(data.data)
        : setError(data.message)
    } catch {
      setError('无法连接到 API 服务')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="empty-state">{error}</div>
  if (!result) return <div className="empty-state">输入查询条件开始搜索</div>
  return <div>{/* 数据展示 */}</div>
}
```

约定：`data.code === 0` 是后端成功标志；每个面板独立管理 loading/result/error 状态。

## API 配置 — Vite 代理

```js
// config.js
const API_BASE = '/api/v1'
export default API_BASE

// vite.config.js（开发环境代理）
proxy: { '/api': { target: 'http://localhost:8000' } }
```

开发环境 Vite 代理 `/api` → FastAPI；生产环境同域直接请求。

## CSS Design Token 系统

```css
:root {
  --accent: #0071e3;
  --space-4: 16px;
  --radius-sm: 8px;
  --motion-fast: 150ms;
}
.card { border-radius: var(--radius-lg); padding: var(--space-6); }
```

Apple 风格设计系统。组件样式用 `.component-name` 命名，工具类用 `.mt-4`, `.flex` 等。

## Architectural Boundaries

- **NO routing library**: 标签页切换用 `useState`，URL 不变
- **NO state management library**: 纯 `useState` + props drilling
- **NO TypeScript**: 全部 `.jsx`，无类型安全
- **NO code splitting**: 所有组件在 App.jsx 中同步导入
- **`esc()` 函数重复**: 5 个文件中有相同的 XSS 转义函数（已知技术债务）

<important if="you are adding a new tab panel to the React frontend">
## Adding a New Panel
1. 创建 `frontend/src/components/NewPanel.jsx`，使用三态模式（loading/result/error）
2. 导入 `API_BASE` from `'../config'`
3. 在 `App.jsx` 导入组件
4. 在标签栏添加按钮 + `activeTab === 'newTab'` 逻辑
5. 添加条件渲染：`{activeTab === 'newTab' && <NewPanel />}`
6. 如需 HeroSearch 数据，通过 props 传入
7. API 调用使用 `fetch(\`${API_BASE}/endpoint\`)`，检查 `data.code === 0`
</important>

<important if="you are adding a new API call to an existing panel">
## Adding a New API Call
1. 在面板组件内添加 `async function`
2. 使用 `fetch(\`${API_BASE}/endpoint?param=${encodeURIComponent(val)}\`)`
3. 检查 `data.code === 0 && data.data` 判断成功
4. 设置 `result` / `error` 状态
5. 用 `try/catch/finally` 包裹，`finally` 中 `setLoading(false)`
</important>
