import { useState, useEffect, useRef } from "react";
import API_BASE from "../config";

export default function ImportPanel({ onImportComplete }) {
	const [file, setFile] = useState(null);
	const [uploading, setUploading] = useState(false);
	const [dragOver, setDragOver] = useState(false);
	const [importHistory, setImportHistory] = useState([]);
	const fileInputRef = useRef(null);

	useEffect(() => {
		fetchImportHistory();
	}, []);

	async function fetchImportHistory() {
		try {
			const resp = await fetch(`${API_BASE}/import/history?limit=10`);
			const data = await resp.json();
			if (data.code === 0 && data.data) {
				setImportHistory(data.data.logs || []);
			}
		} catch {}
	}

	function handleDragOver(e) {
		e.preventDefault();
		setDragOver(true);
	}

	function handleDragLeave() {
		setDragOver(false);
	}

	function handleDrop(e) {
		e.preventDefault();
		setDragOver(false);
		const droppedFile = e.dataTransfer.files[0];
		if (droppedFile) {
			setFile(droppedFile);
		}
	}

	function handleFileSelect(e) {
		const selectedFile = e.target.files[0];
		if (selectedFile) {
			setFile(selectedFile);
		}
	}

	async function handleUpload() {
		if (!file) return;
		setUploading(true);
		try {
			const formData = new FormData();
			formData.append("file", file);
			const resp = await fetch(`${API_BASE}/import/upload`, {
				method: "POST",
				body: formData,
			});
			const data = await resp.json();
			if (data.code === 0) {
				onImportComplete?.();
				setFile(null);
				fetchImportHistory();
			} else {
				alert(data.message || "导入失败");
			}
		} catch (e) {
			alert("上传失败，请检查网络");
		} finally {
			setUploading(false);
		}
	}

	function formatFileSize(bytes) {
		if (!bytes) return "-";
		if (bytes < 1024) return bytes + " B";
		if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
		return (bytes / 1048576).toFixed(1) + " MB";
	}

	function formatTime(ts) {
		if (!ts) return "-";
		try {
			return new Date(ts).toLocaleString("zh-CN");
		} catch {
			return ts;
		}
	}

	return (
		<div>
			<div className="page-header">
				<div>
					<h1 className="page-title">数据导入</h1>
					<p className="page-subtitle">
						上传 aTrust 导出的日志文件，系统将自动解析并导入虚拟IP数据
					</p>
				</div>
			</div>

			<div className="import-layout">
				<div className="import-left">
					{/* 上传区 */}
					<div
						className={`upload-zone ${dragOver ? "drag-over" : ""}`}
						onDragOver={handleDragOver}
						onDragLeave={handleDragLeave}
						onDrop={handleDrop}
						onClick={() => fileInputRef.current?.click()}
					>
						<div className="upload-icon">
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								strokeWidth="2"
							>
								<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
								<polyline points="17 8 12 3 7 8" />
								<line x1="12" y1="3" x2="12" y2="15" />
							</svg>
						</div>
						{file ? (
							<div style={{ textAlign: "center" }}>
								<p style={{ color: "var(--text-primary)", fontWeight: 500 }}>
									{file.name}
								</p>
								<p className="text-xs text-muted mt-2">
									{formatFileSize(file.size)}
								</p>
							</div>
						) : (
							<>
								<p style={{ color: "var(--text-primary)" }}>
									拖拽文件到此处，或点击选择文件
								</p>
								<p className="text-xs text-muted">
									支持 CSV、Excel 格式，最大 50MB
								</p>
							</>
						)}
						<input
							ref={fileInputRef}
							type="file"
							accept=".csv,.xlsx,.xls"
							onChange={handleFileSelect}
							style={{ display: "none" }}
						/>
					</div>

					<button
						className="btn btn-primary"
						style={{ alignSelf: "center" }}
						onClick={handleUpload}
						disabled={!file || uploading}
					>
						{uploading ? "导入中..." : "选择文件导入"}
					</button>

					{/* 导入历史 */}
					<div>
						<h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
							最近导入记录
						</h3>
						<div className="card">
							<div className="table-header">
								<span style={{ flex: 1, minWidth: 0, padding: "0 16px" }}>
									文件名
								</span>
								<span style={{ width: 140, padding: "0 16px" }}>导入条数</span>
								<span style={{ width: 120, padding: "0 16px" }}>状态</span>
								<span style={{ width: 180, padding: "0 16px" }}>导入时间</span>
							</div>
							{importHistory.length === 0 ? (
								<div className="card-body text-center">
									<p className="text-muted text-xs">暂无导入记录</p>
								</div>
							) : (
								importHistory.map((log) => (
									<div key={log.id} className="table-row">
										<span
											className="text-mono"
											style={{
												flex: 1,
												minWidth: 0,
												overflow: "hidden",
												textOverflow: "ellipsis",
												whiteSpace: "nowrap",
												padding: "0 16px",
											}}
										>
											{log.filename}
										</span>
										<span
											className="text-secondary text-mono"
											style={{ width: 140, padding: "0 16px" }}
										>
											{(log.record_count || 0).toLocaleString()}
										</span>
										<span style={{ width: 120, padding: "0 16px" }}>
											<span
												className={`badge ${log.status === "success" ? "badge-success" : log.status === "partial" ? "badge-warning" : "badge-offline"}`}
											>
												{log.status === "success"
													? "成功"
													: log.status === "partial"
														? "部分成功"
														: log.status === "failed"
															? "失败"
															: log.status}
											</span>
										</span>
										<span
											className="text-muted text-mono"
											style={{ width: 180, padding: "0 16px" }}
										>
											{formatTime(log.created_at)}
										</span>
									</div>
								))
							)}
						</div>
					</div>
				</div>

				<div className="import-right">
					{/* 导入说明 */}
					<div className="card">
						<div className="card-header">
							<div className="card-title">
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--accent)"
									strokeWidth="2"
								>
									<circle cx="12" cy="12" r="10" />
									<line x1="12" y1="16" x2="12" y2="12" />
									<line x1="12" y1="8" x2="12.01" y2="8" />
								</svg>
								导入说明
							</div>
						</div>
						<div
							className="card-body"
							style={{ display: "flex", flexDirection: "column", gap: 14 }}
						>
							<div className="step-item">
								<div className="step-num">1</div>
								<span className="step-text">
									登录 aTrust 控制台，进入日志导出页面
								</span>
							</div>
							<div className="step-item">
								<div className="step-num">2</div>
								<span className="step-text">
									选择时间范围，导出访问日志为 CSV 格式
								</span>
							</div>
							<div className="step-item">
								<div className="step-num">3</div>
								<span className="step-text">上传导出的文件到本系统</span>
							</div>
							<div className="step-item">
								<div className="step-num">4</div>
								<span className="step-text">系统自动解析并导入虚拟IP数据</span>
							</div>
						</div>
					</div>

					{/* 支持格式 */}
					<div className="card">
						<div className="card-header">
							<div className="card-title">
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--success)"
									strokeWidth="2"
								>
									<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
									<polyline points="14 2 14 8 20 8" />
									<line x1="16" y1="13" x2="8" y2="13" />
									<line x1="16" y1="17" x2="8" y2="17" />
								</svg>
								支持的文件格式
							</div>
						</div>
						<div
							className="card-body"
							style={{ display: "flex", flexDirection: "column", gap: 12 }}
						>
							<div className="format-tag">
								<span className="format-ext csv">.csv</span>
								<span className="text-secondary text-xs">
									aTrust 导出的 CSV 日志文件
								</span>
							</div>
							<div className="format-tag">
								<span className="format-ext xlsx">.xlsx</span>
								<span className="text-secondary text-xs">
									Excel 格式的数据文件
								</span>
							</div>
							<div className="format-tag">
								<span className="format-ext xls">.xls</span>
								<span className="text-secondary text-xs">
									旧版 Excel 格式文件
								</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
