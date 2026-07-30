import { useState, useEffect } from 'react'
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

export default function ReversePanel({ queryInput, queryType }) {
  const [ip, setIp] = useState('')
  const [limit, setLimit] = useState(10)
  const [loading, setLoading] = useState(false)
  const [records, setRecords] = useState(null)
  const [virtualIp, setVirtualIp] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    if (queryInput && queryType === 'ip') {
      setIp(queryInput)
      performReverseQuery(queryInput, limit)
    }
  }, [queryInput, queryType])

  async function performReverseQuery(ipValue, limitValue) {
    if (!ipValue) {
      setError('请输入虚拟IP地址')
      return
    }

    setLoading(true)
    setError(null)
    setRecords(null)

    try {
      const resp = await fetch(`${API_BASE}/vip/reverse?ip=${encodeURIComponent(ipValue)}&limit=${limitValue}`)
      const data = await resp.json()

      if (data.code === 0 && data.data && data.data.records?.length > 0) {
        setRecords(data.data.records)
        setVirtualIp(data.data.virtual_ip)
      } else {
        setError('未找到关联记录')
      }
    } catch (err) {
      setError('无法连接到 API 服务')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="tab-panel active">
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M17 1l4 4-4 4" />
              <path d="M3 11V9a4 4 0 014-4h14" />
              <path d="M7 23l-4-4 4-4" />
              <path d="M21 13v2a4 4 0 01-4 4H3" />
            </svg>
            按虚拟IP反查用户
          </div>
        </div>
        <div className="form-row">
          <div className="form-group" style={{ flex: 2 }}>
            <label className="form-label" htmlFor="reverse-ip">虚拟IP地址</label>
            <input
              type="text"
              className="form-input"
              id="reverse-ip"
              placeholder="例如: 10.10.10.100"
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && performReverseQuery(ip, limit)}
            />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label" htmlFor="reverse-limit">返回条数</label>
            <input
              type="number"
              className="form-input"
              id="reverse-limit"
              value={limit}
              min="1"
              max="100"
              onChange={(e) => setLimit(parseInt(e.target.value) || 10)}
            />
          </div>
          <div className="form-group" style={{ flex: 0, justifyContent: 'flex-end' }}>
            <label className="form-label">&nbsp;</label>
            <button
              className="btn btn-primary"
              onClick={() => performReverseQuery(ip, limit)}
              disabled={loading}
            >
              {loading ? '查询中...' : '反查'}
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
              <div className="empty-desc">该虚拟IP地址暂无关联的用户记录</div>
            </div>
          )}

          {!loading && records && (
            <>
              <div className="flex items-center justify-between mb-4">
                <span className="text-mono" style={{ fontSize: 'var(--text-sm)', color: 'var(--muted)' }}>
                  虚拟IP: {esc(virtualIp)} · 共 {records.length} 条记录
                </span>
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>用户名</th>
                    <th>显示名</th>
                    <th>真实IP</th>
                    <th>事件类型</th>
                    <th>时间</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((r, i) => (
                    <tr key={i}>
                      <td className="mono">{esc(r.user_name)}</td>
                      <td>{esc(r.display_name || '-')}</td>
                      <td className="mono">{esc(r.real_ip || '-')}</td>
                      <td><span className="badge badge-info">{esc(r.event_type)}</span></td>
                      <td className="mono">{esc(r.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
