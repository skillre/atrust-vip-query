import { useState } from 'react'

export default function HeroSearch({ onSearch }) {
  const [input, setInput] = useState('')
  const [type, setType] = useState('user')

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleSearch = () => {
    if (input.trim()) {
      onSearch(input.trim(), type)
    }
  }

  return (
    <section className="hero-search">
      <div className="container">
        <h1>虚拟IP查询</h1>
        <p className="lead">
          快速查询 aTrust 零信任系统分配给用户的虚拟IP地址，支持用户名查询和IP反查
        </p>
        <div className="search-box">
          <div className="search-input-wrap">
            <input
              type="text"
              placeholder="输入用户名、显示名或虚拟IP地址..."
              autoComplete="off"
              aria-label="搜索用户名或IP地址"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              aria-label="搜索类型"
            >
              <option value="user">按用户查询</option>
              <option value="ip">按IP反查</option>
            </select>
            <button
              className="search-btn"
              onClick={handleSearch}
              aria-label="执行查询"
            >
              查询
            </button>
          </div>
          <p className="search-hint">支持模糊搜索 · 按 Enter 快速查询</p>
        </div>
      </div>
    </section>
  )
}
