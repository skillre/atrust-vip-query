import { useState, useRef } from 'react'
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

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

export default function ImportPanel({ onImportComplete }) {
  const [dragOver, setDragOver] = useState(false)
  const [preview, setPreview] = useState(null)
  const [importResult, setImportResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [pendingFile, setPendingFile] = useState(null)
  const fileInputRef = useRef(null)

  function handleDragOver(e) {
    e.preventDefault()
    setDragOver(true)
  }

  function handleDragLeave() {
    setDragOver(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  function handleFileSelect(e) {
    if (e.target.files.length > 0) {
      handleFile(e.target.files[0])
    }
  }

  async function handleFile(file) {
    const allowed = ['.csv', '.xlsx', '.xls']
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!allowed.includes(ext)) {
      return
    }

    setPreview(null)
    setImportResult(null)
    setLoading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const resp = await fetch(`${API_BASE}/import/preview`, {
        method: 'POST',
        body: formData,
      })
      const data = await resp.json()

      if (data.code === 0 && data.data) {
        setPreview({ ...data.data, fileName: file.name, fileSize: file.size })
        setPendingFile(file)
      } else {
        setPreview({ error: data.message || '解析失败' })
      }
    } catch (err) {
      setPreview({ error: '文件解析失败，请检查文件格式' })
    } finally {
      setLoading(false)
    }
  }

  async function importFile() {
    if (!pendingFile) return

    setImporting(true)
    setImportResult(null)

    const formData = new FormData()
    formData.append('file', pendingFile)

    try {
      const resp = await fetch(`${API_BASE}/import/upload`, {
        method: 'POST',
        body: formData,
      })
      const data = await resp.json()

      if (data.code === 0 && data.data) {
        setImportResult({ success: true, ...data.data })
        if (onImportComplete) onImportComplete()
      } else {
        setImportResult({ success: false, message: data.message || '导入失败' })
      }
    } catch (err) {
      setImportResult({ success: false, message: '导入失败，请稍后重试' })
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="tab-panel active">
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="17,8 12,3 7,8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            数据导入
          </div>
          <span className="badge badge-info">CSV / Excel</span>
        </div>

        <div
          className={`import-zone ${dragOver ? 'dragover' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          aria-label="点击或拖拽文件到此处上传"
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              fileInputRef.current?.click()
            }
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            accept=".csv,.xlsx,.xls"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
          <svg className="import-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="17,8 12,3 7,8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <div className="import-text">点击或拖拽文件到此处上传</div>
          <div className="import-hint">支持 CSV、XLSX、XLS 格式，单个文件最大 50MB</div>
        </div>

        <div className="mt-6">
          {loading && (
            <div className="text-center mt-4">
              <div className="spinner" style={{ margin: '0 auto' }}></div>
              <p className="mt-4" style={{ color: 'var(--muted)' }}>正在解析文件...</p>
            </div>
          )}

          {!loading && preview && preview.error && (
            <div className="card" style={{ borderColor: 'var(--danger)' }}>
              <div className="flex items-center gap-3">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M15 9l-6 6M9 9l6 6" />
                </svg>
                <span style={{ color: 'var(--danger)' }}>{esc(preview.error)}</span>
              </div>
            </div>
          )}

          {!loading && preview && !preview.error && (
            <div className="card" style={{ background: 'var(--surface-warm)' }}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <strong>{esc(preview.fileName)}</strong>
                  <span className="text-mono" style={{ color: 'var(--muted)', marginLeft: '8px' }}>
                    {formatSize(preview.fileSize)}
                  </span>
                </div>
                <span className="badge badge-online">解析成功</span>
              </div>
              <div className="stats-row" style={{ marginBottom: 0 }}>
                <div className="stat-card">
                  <div className="stat-value">{(preview.total_rows || 0).toLocaleString()}</div>
                  <div className="stat-label">总行数</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{(preview.columns || []).length}</div>
                  <div className="stat-label">列数</div>
                </div>
              </div>

              {preview.preview && preview.preview.length > 0 && (
                <div style={{ overflowX: 'auto', marginTop: '16px' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        {Object.keys(preview.preview[0]).map((c) => (
                          <th key={c}>{esc(c)}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.preview.slice(0, 5).map((row, i) => (
                        <tr key={i}>
                          {Object.keys(row).map((c) => (
                            <td key={c} className="mono">{esc(String(row[c] || ''))}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="flex gap-3 mt-4" style={{ justifyContent: 'flex-end' }}>
                <button
                  className="btn btn-primary"
                  onClick={importFile}
                  disabled={importing}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17,8 12,3 7,8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  {importing ? '导入中...' : '开始导入'}
                </button>
              </div>
            </div>
          )}

          {!loading && importResult && (
            <div className="mt-4">
              {importResult.success ? (
                <div className="card" style={{ borderColor: 'var(--success)' }}>
                  <div className="flex items-center gap-3 mb-4">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M8 12l3 3 5-5" />
                    </svg>
                    <strong style={{ color: 'var(--success)' }}>{esc(importResult.message || '导入成功')}</strong>
                  </div>
                  <div className="stats-row" style={{ marginBottom: 0 }}>
                    <div className="stat-card">
                      <div className="stat-value">{(importResult.total_rows || 0).toLocaleString()}</div>
                      <div className="stat-label">总行数</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{(importResult.imported || 0).toLocaleString()}</div>
                      <div className="stat-label">成功导入</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{(importResult.skipped || 0).toLocaleString()}</div>
                      <div className="stat-label">跳过</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{(importResult.errors || 0).toLocaleString()}</div>
                      <div className="stat-label">错误</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="card" style={{ borderColor: 'var(--danger)' }}>
                  <div className="flex items-center gap-3">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M15 9l-6 6M9 9l6 6" />
                    </svg>
                    <span style={{ color: 'var(--danger)' }}>{esc(importResult.message || '导入失败')}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
