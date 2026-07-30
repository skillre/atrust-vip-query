import { useState } from 'react'

export default function Nav({ activeTab, onTabChange, systemStatus }) {
  return (
    <header className="topnav">
      <div className="container topnav-inner">
        <span className="logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          aTrust 虚拟IP查询
        </span>
        <nav>
          <a
            href="#"
            className={activeTab === 'query' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); onTabChange('query') }}
          >
            查询
          </a>
          <a
            href="#"
            className={activeTab === 'history' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); onTabChange('history') }}
          >
            历史记录
          </a>
          <a
            href="#"
            className={activeTab === 'import' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); onTabChange('import') }}
          >
            数据导入
          </a>
          <a
            href="#"
            className={activeTab === 'export' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); onTabChange('export') }}
          >
            数据导出
          </a>
        </nav>
        <div className="flex items-center gap-3">
          <span className={`badge ${systemStatus === 'healthy' ? 'badge-online' : systemStatus === 'checking' ? 'badge-neutral' : 'badge-offline'}`}>
            <span className="badge-dot"></span>
            {systemStatus === 'healthy' ? '系统正常' : systemStatus === 'checking' ? '检查中...' : '未连接'}
          </span>
        </div>
      </div>
    </header>
  )
}
