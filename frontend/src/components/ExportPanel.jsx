import { useState } from "react";
import API_BASE from "../config";

export default function ExportPanel() {
	const [name, setName] = useState("");
	const [days, setDays] = useState(30);
	const [type, setType] = useState("");
	const [loading, setLoading] = useState(false);
	const [preview, setPreview] = useState(null);

	async function previewExport() {
		setLoading(true);
		setPreview(null);

		try {
			let url = `${API_BASE}/vip/history?days=${days}&page=1&page_size=50`;
			if (name) url += `&name=${encodeURIComponent(name)}`;
			const resp = await fetch(url);
			const data = await resp.json();

			if (data.code === 0 && data.data && data.data.records?.length > 0) {
				setPreview({ records: data.data.records, total: data.data.total });
			} else {
				setPreview({ records: [], total: 0 });
			}
		} catch (err) {
			setPreview({ records: [], total: 0 });
		} finally {
			setLoading(false);
		}
	}

	function downloadExport() {
		let url = `${API_BASE}/export/csv?days=${days}`;
		if (name) url += `&name=${encodeURIComponent(name)}`;
		if (type) url += `&event_type=${encodeURIComponent(type)}`;

		const link = document.createElement("a");
		link.href = url;
		link.target = "_blank";
		link.rel = "noopener noreferrer";
		link.click();
	}

	return (
		<div className="tab-panel active">
			<div className="card">
				<div className="card-header">
					<div className="card-title">
						<svg
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							strokeWidth="1.6"
						>
							<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
							<polyline points="7,10 12,15 17,10" />
							<line x1="12" y1="15" x2="12" y2="3" />
						</svg>
						数据导出
					</div>
				</div>
				<div className="form-row">
					<div className="form-group">
						<label className="form-label" htmlFor="export-name">
							用户名筛选（可选）
						</label>
						<input
							type="text"
							className="form-input"
							id="export-name"
							placeholder="留空导出全部"
							value={name}
							onChange={(e) => setName(e.target.value)}
						/>
					</div>
					<div className="form-group">
						<label className="form-label" htmlFor="export-days">
							导出天数
						</label>
						<input
							type="number"
							className="form-input"
							id="export-days"
							value={days}
							min="1"
							max="365"
							onChange={(e) => setDays(parseInt(e.target.value) || 30)}
						/>
					</div>
					<div className="form-group">
						<label className="form-label" htmlFor="export-type">
							事件类型
						</label>
						<select
							className="form-input"
							id="export-type"
							value={type}
							onChange={(e) => setType(e.target.value)}
						>
							<option value="">全部类型</option>
							<option value="csv_import">CSV导入</option>
							<option value="syslog_access">访问</option>
							<option value="syslog_vip_apply">分配</option>
							<option value="syslog_vip_revoke">释放</option>
						</select>
					</div>
				</div>
				<div className="flex gap-3 mt-4">
					<button
						className="btn btn-secondary"
						onClick={previewExport}
						disabled={loading}
					>
						{loading ? "预览中..." : "预览数据"}
					</button>
					<button className="btn btn-primary" onClick={downloadExport}>
						<svg
							width="16"
							height="16"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							strokeWidth="2"
						>
							<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
							<polyline points="7,10 12,15 17,10" />
							<line x1="12" y1="15" x2="12" y2="3" />
						</svg>
						下载 CSV
					</button>
				</div>

				<div className="mt-6">
					{loading && (
						<div className="text-center mt-4">
							<div className="spinner" style={{ margin: "0 auto" }}></div>
						</div>
					)}

					{!loading && preview && (
						<>
							{preview.records.length === 0 ? (
								<div className="empty-state" style={{ padding: "24px" }}>
									<div className="empty-desc">未找到符合条件的数据</div>
								</div>
							) : (
								<>
									<div className="flex items-center justify-between mb-4">
										<span
											className="text-mono"
											style={{
												fontSize: "var(--text-sm)",
												color: "var(--muted)",
											}}
										>
											预览前 {preview.records.length} 条 · 共 {preview.total} 条
										</span>
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
											{preview.records.map((r, i) => (
												<tr key={i}>
													<td className="mono">{r.virtual_ip}</td>
													<td className="mono">{r.real_ip || "-"}</td>
													<td>
														<span className="badge badge-info">
															{r.event_type}
														</span>
													</td>
													<td className="mono">{r.timestamp}</td>
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
	);
}
