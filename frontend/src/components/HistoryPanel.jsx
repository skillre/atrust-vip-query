import { useState } from 'react'
import API_BASE from '../config'

function esc(str) {
  if (str == null) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export default function HistoryPanel() {
  const [name, setName] = useState('')
  const [days, setDays] = useState(30)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function performHistoryQuery() {
    if (!name) {
      setError('请输入用户名')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const resp = await fetch(
        `${API_BASE}/vip/history?name=${encodeURIComponent(name)}&days=${days}&page=${page}&page_size=${pageSize}`
      )
      const data = await resp.json()

      if (data.code === 0 && data.data) {
        setResult(data.data)
      } else {
        setError(data.message || '查询失败')
      }
    } catch (err) {
      setError('无法连接到 API 服务')
    } finally {
      setLoading(false)
    }
  }

  function exportHistoryCSV() {
    const url = `${API_BASE}/export/csv?name=${encodeURIComponent(name)}&days=${days}`
    const link = document.createElement('a')
    link.href = url
    link.target = '_blank'
    link.rel = 'noopener noreferrer'
    link.click()
  }

  return (
    <div className="tab-panel active">
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12,6 12,12 16,14" />
            </svg>
            历史记录查询
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label" htmlFor="history-name">用户名或显示名</label>
            <input
              type="text"
              className="form-input"
              id="history-name"
              placeholder="例如: zhangsan"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && performHistoryQuery()}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="history-days">查询天数</label>
            <input
              type="number"
              className="form-input"
              id="history-days"
              value={days}
              min="1"
              max="365"
              onChange={(e) => setDays(parseInt(e.target.value) || 30)}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="history-page">页码</label>
            <input
              type="number"
              className="form-input"
              id="history-page"
              value={page}
              min="1"
              onChange={(e) => setPage(parseInt(e.target.value) || 1)}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="history-page-size">每页条数</label>
            <input
              type="number"
              className="form-input"
              id="history-page-size"
              value={pageSize}
              min="10"
              max="100"
              onChange={(e) => setPageSize(parseInt(e.target.value) || 20)}
            />
          </div>
          <div className="form-group" style={{ justifyContent: 'flex-end' }}>
            <label className="form-label">&nbsp;</label>
            <button
              className="btn btn-primary"
              onClick={performHistoryQuery}
              disabled={loading}
            >
              {loading ? '查询中...' : '查询'}
            </button>
          </div>
        </div>

        <div className="mt-6">
          {loading && (
            <div className="text-center mt-4">
              <div className="spinner" style={{ margin: '0 auto' }}></div>
            </div>
          )}

          {!loading && error && (
            <div className="empty-state" style={{ padding: '32px' }}>
              <div className="empty-title">{error}</div>
            </div>
          )}

          {!loading && result && (
            <>
              {!result.records || result.records.length === 0 ? (
                <div className="empty-state" style={{ padding: '32px' }}>
                  <div className="empty-title">未找到历史记录</div>
                  <div className="empty-desc">该用户在指定时间范围内暂无记录</div>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4" style={{ flexWrap: 'wrap', gap: '12px' }}>
                    <span className="text-mono" style={{ fontSize: 'var(--text-sm)', color: 'var(--muted)' }}>
                      共 {result.total} 条记录 · 第 {result.page} 页 · 每页 {result.page_size} 条
                    </span>
                    <button className="btn btn-sm btn-secondary" onClick={exportHistoryCSV}>
                      导出 CSV
                    </button>
                  </div>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>虚拟IP</th>
                        <th>真实IP</th>
                        <th>事件类型</th>
                        <th>时间</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.records.map((r, i) => (
                        <tr key={i}>
                          <td className="mono">{esc(r.virtual_ip)}</td>
                          <td className="mono">{esc(r.real_ip || '-')}</td>
                          <td><span className="badge badge-info">{esc(r.event_type)}</span></td>
                          <td className="mono">{esc(r.timestamp)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
