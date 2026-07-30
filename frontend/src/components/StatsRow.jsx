import { useState, useEffect } from 'react'
import API_BASE from '../config'

export default function StatsRow() {
  const [stats, setStats] = useState({ users: '-', records: '-', online: '-', today: '-' })

  useEffect(() => {
    loadStats()
  }, [])

  async function loadStats() {
    try {
      const resp = await fetch(`${API_BASE}/system/stats`)
      const data = await resp.json()

      if (data.code === 0 && data.data) {
        const db = data.data.database || {}
        setStats({
          users: (db.user_count || 0).toLocaleString(),
          records: (db.record_count || 0).toLocaleString(),
          online: '-',
          today: '-'
        })
      }
    } catch (err) {
      // Silent fail for stats
    }
  }

  return (
    <div className="stats-row">
      <div className="stat-card">
        <div className="stat-value">{stats.users}</div>
        <div className="stat-label">用户总数</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.records}</div>
        <div className="stat-label">记录总数</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.online}</div>
        <div className="stat-label">在线用户</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.today}</div>
        <div className="stat-label">今日查询</div>
      </div>
    </div>
  )
}
