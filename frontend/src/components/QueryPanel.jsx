import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API_BASE from "../config";

export default function QueryPanel({ queryInput, queryType }) {
	const [result, setResult] = useState(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState("");
	const [recentSearches, setRecentSearches] = useState([]);
	const [fuzzy, setFuzzy] = useState(false); // 模糊匹配开关
	const navigate = useNavigate();

	useEffect(() => {
		fetchRecent();
	}, []);

	useEffect(() => {
		if (queryInput && queryType !== "ip") {
			doQuery(queryInput);
		}
	}, [queryInput, queryType]);

	async function fetchRecent() {
		try {
			const resp = await fetch(`${API_BASE}/search/recent?limit=5`);
			const data = await resp.json();
			if (data.code === 0 && data.data) {
				setRecentSearches(data.data.searches || []);
			}
		} catch {}
	}

	async function doQuery(name) {
		if (!name) return;
		setLoading(true);
		setError("");
		setResult(null);
		try {
			const resp = await fetch(
				`${API_BASE}/vip/query?name=${encodeURIComponent(name)}&source=all&fuzzy=${fuzzy}`,
			);
			const data = await resp.json();
			if (data.code === 0 && data.data) {
				setResult(data.data);
			} else {
				setError(data.message || "查询失败");
			}
		} catch (e) {
			setError("网络错误，请检查后端服务");
		} finally {
			setLoading(false);
		}
	}

	function getInitial(name) {
		if (!name) return "?";
		return name.charAt(0).toUpperCase();
	}

	function getDepartment(result) {
		if (result.display_name && result.user_name) {
			return result.display_name;
		}
		return "";
	}

	if (!queryInput) {
		return (
			<div className="main-content">
				<div className="main-left">
					{/* Fuzzy Toggle */}
					<div
						style={{
							marginBottom: 16,
							display: "flex",
							alignItems: "center",
							gap: 8,
						}}
					>
						<label
							style={{
								fontSize: 14,
								color: "var(--text-secondary)",
								display: "flex",
								alignItems: "center",
								gap: 6,
								cursor: "pointer",
							}}
						>
							<input
								type="checkbox"
								checked={fuzzy}
								onChange={(e) => setFuzzy(e.target.checked)}
								style={{ width: 16, height: 16 }}
							/>
							模糊匹配（可匹配多个用户）
						</label>
					</div>
					<div className="card">
						<div
							className="card-body text-center"
							style={{ padding: "60px 20px" }}
						>
							<svg
								width="48"
								height="48"
								viewBox="0 0 24 24"
								fill="none"
								stroke="var(--text-muted)"
								strokeWidth="1.5"
								style={{ margin: "0 auto 16px" }}
							>
								<circle cx="11" cy="11" r="8" />
								<path d="M21 21l-4.35-4.35" />
							</svg>
							<p style={{ color: "var(--text-secondary)", fontSize: "15px" }}>
								在上方搜索框输入用户名或IP地址开始查询
							</p>
						</div>
					</div>
				</div>
				<div className="main-right">
					<Sidebar
						recentSearches={recentSearches}
						onQuickAction={(path) => navigate(path)}
					/>
				</div>
			</div>
		);
	}

	if (loading) {
		return (
			<div className="main-content">
				<div className="main-left">
					<div
						style={{
							marginBottom: 16,
							display: "flex",
							alignItems: "center",
							gap: 8,
						}}
					>
						<label
							style={{
								fontSize: 14,
								color: "var(--text-secondary)",
								display: "flex",
								alignItems: "center",
								gap: 6,
								cursor: "pointer",
							}}
						>
							<input
								type="checkbox"
								checked={fuzzy}
								onChange={(e) => setFuzzy(e.target.checked)}
								style={{ width: 16, height: 16 }}
							/>
							模糊匹配（可匹配多个用户）
						</label>
					</div>
					<div className="card">
						<div
							className="card-body text-center"
							style={{ padding: "60px 20px" }}
						>
							<p style={{ color: "var(--text-secondary)" }}>查询中...</p>
						</div>
					</div>
				</div>
				<div className="main-right">
					<Sidebar
						recentSearches={recentSearches}
						onQuickAction={(path) => navigate(path)}
					/>
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="main-content">
				<div className="main-left">
					<div
						style={{
							marginBottom: 16,
							display: "flex",
							alignItems: "center",
							gap: 8,
						}}
					>
						<label
							style={{
								fontSize: 14,
								color: "var(--text-secondary)",
								display: "flex",
								alignItems: "center",
								gap: 6,
								cursor: "pointer",
							}}
						>
							<input
								type="checkbox"
								checked={fuzzy}
								onChange={(e) => setFuzzy(e.target.checked)}
								style={{ width: 16, height: 16 }}
							/>
							模糊匹配（可匹配多个用户）
						</label>
					</div>
					<div className="card">
						<div
							className="card-body text-center"
							style={{ padding: "60px 20px" }}
						>
							<p style={{ color: "var(--error)" }}>{error}</p>
						</div>
					</div>
				</div>
				<div className="main-right">
					<Sidebar
						recentSearches={recentSearches}
						onQuickAction={(path) => navigate(path)}
					/>
				</div>
			</div>
		);
	}

	if (!result) return null;

	// 模糊/批量查询命中多个用户：展开列表
	if (Array.isArray(result.matches)) {
		const matches = result.matches;
		return (
			<div className="main-content">
				<div className="main-left">
					<div
						style={{
							marginBottom: 16,
							display: "flex",
							alignItems: "center",
							gap: 8,
						}}
					>
						<label
							style={{
								fontSize: 14,
								color: "var(--text-secondary)",
								display: "flex",
								alignItems: "center",
								gap: 6,
								cursor: "pointer",
							}}
						>
							<input
								type="checkbox"
								checked={fuzzy}
								onChange={(e) => setFuzzy(e.target.checked)}
								style={{ width: 16, height: 16 }}
							/>
							模糊匹配（可匹配多个用户）
						</label>
					</div>
					<div className="card">
						<div className="card-header">
							<span className="card-title">匹配到 {matches.length} 个用户</span>
						</div>
						{matches.length === 0 ? (
							<div className="card-body text-center" style={{ padding: 40 }}>
								<p className="text-muted">未找到匹配用户</p>
							</div>
						) : (
							<>
								<div className="table-header">
									<span style={{ width: 140 }}>用户名</span>
									<span style={{ width: 140 }}>显示名</span>
									<span style={{ width: 150 }}>当前虚拟IP</span>
									<span style={{ width: 150 }}>真实IP</span>
									<span style={{ width: 180 }}>最近时间</span>
								</div>
								{matches.map((m, idx) => {
									const v = m.history_vip;
									return (
										<div className="table-row" key={m.user_name || idx}>
											<span style={{ width: 140, fontWeight: 500 }}>
												{m.user_name}
											</span>
											<span className="text-secondary" style={{ width: 140 }}>
												{m.display_name || "-"}
											</span>
											<span
												className="col-accent"
												style={{ width: 150, fontFamily: "var(--font-mono)" }}
											>
												{v ? v.virtual_ip : "-"}
											</span>
											<span
												className="text-secondary"
												style={{ width: 150, fontFamily: "var(--font-mono)" }}
											>
												{v && v.real_ip ? v.real_ip : "-"}
											</span>
											<span
												className="text-muted"
												style={{ width: 180, fontFamily: "var(--font-mono)" }}
											>
												{v && v.timestamp
													? new Date(v.timestamp).toLocaleString("zh-CN")
													: "-"}
											</span>
										</div>
									);
								})}
							</>
						)}
					</div>
				</div>
				<div className="main-right">
					<Sidebar
						recentSearches={recentSearches}
						onQuickAction={(path) => navigate(path)}
					/>
				</div>
			</div>
		);
	}

	const isOnline = result.is_online;
	const vip = result.history_vip;
	const onlineVip =
		result.online_vips && result.online_vips.length > 0
			? result.online_vips[0]
			: null;
	const displayVip =
		onlineVip ||
		(vip
			? {
					ip: vip.virtual_ip,
					real_ip: vip.real_ip,
					last_login_time: vip.timestamp,
				}
			: null);

	return (
		<div className="main-content">
			<div className="main-left">
				{/* 用户结果卡 */}
				<div className="card">
					<div className="user-result-header">
						<div className="user-info">
							<div className="avatar">{getInitial(result.user_name)}</div>
							<div>
								<div className="user-name">{result.user_name}</div>
								<div className="user-meta">{getDepartment(result)}</div>
								{result.phone && (
									<div className="user-meta">📱 {result.phone}</div>
								)}
							</div>
						</div>
						{isOnline && (
							<div className="badge badge-online">
								<span className="status-dot" style={{ width: 8, height: 8 }} />
								在线
							</div>
						)}
					</div>
					<div className="card-body">
						{displayVip ? (
							<div className="vip-section">
								<div
									style={{
										display: "flex",
										alignItems: "center",
										gap: 8,
										marginBottom: 8,
									}}
								>
									<svg
										width="16"
										height="16"
										viewBox="0 0 24 24"
										fill="none"
										stroke="var(--online)"
										strokeWidth="2"
									>
										<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
										<polyline points="22 4 12 14.01 9 11.01" />
									</svg>
									<span
										style={{
											fontSize: 13,
											fontWeight: 600,
											color: "var(--text-secondary)",
										}}
									>
										在线虚拟IP
									</span>
								</div>
								<div className="vip-card">
									<div>
										<div className="vip-field-label">虚拟IP</div>
										<div className="vip-field-value large">{displayVip.ip}</div>
									</div>
									<div>
										<div className="vip-field-label">真实IP</div>
										<div className="vip-field-value normal">
											{displayVip.real_ip || "-"}
										</div>
									</div>
									<div>
										<div className="vip-field-label">登录时间</div>
										<div className="vip-field-value small">
											{displayVip.last_login_time
												? new Date(displayVip.last_login_time).toLocaleString(
														"zh-CN",
													)
												: "-"}
										</div>
									</div>
								</div>
							</div>
						) : (
							<p
								style={{
									color: "var(--text-muted)",
									textAlign: "center",
									padding: 20,
								}}
							>
								暂无虚拟IP记录
							</p>
						)}

						<div className="quick-actions mt-4">
							<button
								className="quick-action-btn"
								onClick={() => navigate("/history")}
							>
								<svg
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
								>
									<circle cx="12" cy="12" r="10" />
									<polyline points="12 6 12 12 16 14" />
								</svg>
								查看历史
							</button>
							<button
								className="quick-action-btn"
								onClick={() => navigate("/export")}
							>
								<svg
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
								>
									<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
									<polyline points="7 10 12 15 17 10" />
									<line x1="12" y1="15" x2="12" y2="3" />
								</svg>
								导出记录
							</button>
						</div>
					</div>
				</div>

				{/* 历史IP分配表格 */}
				{result.history_vip && (
					<div className="card">
						<div className="card-header">
							<span className="card-title">历史IP分配记录</span>
							<span className="text-xs text-muted">共 1 条记录</span>
						</div>
						<div className="table-header">
							<span style={{ width: 160 }}>虚拟IP</span>
							<span style={{ width: 160 }}>真实IP</span>
							<span style={{ width: 120 }}>事件类型</span>
							<span style={{ width: 180 }}>时间</span>
						</div>
						<div className="table-row">
							<span
								className="col-accent"
								style={{ width: 160, fontFamily: "var(--font-mono)" }}
							>
								{result.history_vip.virtual_ip}
							</span>
							<span
								className="text-secondary"
								style={{ width: 160, fontFamily: "var(--font-mono)" }}
							>
								{result.history_vip.real_ip || "-"}
							</span>
							<span style={{ width: 120 }}>
								<span
									className={`badge ${result.history_vip.event_type === "上线" ? "badge-online" : "badge-offline"}`}
								>
									{result.history_vip.event_type || "-"}
								</span>
							</span>
							<span
								className="text-muted"
								style={{ width: 180, fontFamily: "var(--font-mono)" }}
							>
								{result.history_vip.timestamp
									? new Date(result.history_vip.timestamp).toLocaleString(
											"zh-CN",
										)
									: "-"}
							</span>
						</div>
					</div>
				)}
			</div>

			<div className="main-right">
				<Sidebar
					recentSearches={recentSearches}
					onQuickAction={(path) => navigate(path)}
				/>
			</div>
		</div>
	);
}

function Sidebar({ recentSearches, onQuickAction }) {
	return (
		<>
			{/* 最近查询 */}
			<div className="card">
				<div className="card-header">
					<span className="card-title">最近查询</span>
					<span
						className="text-xs"
						style={{ color: "var(--accent)", cursor: "pointer" }}
					>
						查看全部
					</span>
				</div>
				{recentSearches.length === 0 ? (
					<div className="card-body text-center">
						<p className="text-muted text-xs">暂无查询记录</p>
					</div>
				) : (
					recentSearches.map((s) => (
						<div key={s.id} className="recent-item">
							<div className="avatar avatar-sm">
								{s.query_text.charAt(0).toUpperCase()}
							</div>
							<div style={{ flex: 1, minWidth: 0 }}>
								<div
									className="recent-name"
									style={{
										overflow: "hidden",
										textOverflow: "ellipsis",
										whiteSpace: "nowrap",
									}}
								>
									{s.query_text}
								</div>
								<div className="recent-meta">
									{s.query_type === "ip" ? "IP反查" : "用户查询"} ·{" "}
									{s.created_at
										? new Date(s.created_at).toLocaleString("zh-CN", {
												month: "numeric",
												day: "numeric",
												hour: "2-digit",
												minute: "2-digit",
											})
										: ""}
								</div>
							</div>
						</div>
					))
				)}
			</div>

			{/* 快捷操作 */}
			<div className="card">
				<div className="card-header">
					<span className="card-title">快捷操作</span>
				</div>
				<div className="quick-grid">
					<div className="quick-item" onClick={() => onQuickAction("/import")}>
						<div
							className="quick-icon"
							style={{
								background: "var(--accent-rgba)",
								color: "var(--accent)",
							}}
						>
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
						<div>
							<div style={{ fontSize: 13, fontWeight: 500 }}>数据导入</div>
							<div className="text-xs text-muted">上传日志文件</div>
						</div>
					</div>
					<div className="quick-item" onClick={() => onQuickAction("/export")}>
						<div
							className="quick-icon"
							style={{
								background: "var(--success-rgba)",
								color: "var(--success)",
							}}
						>
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								strokeWidth="2"
							>
								<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
								<polyline points="7 10 12 15 17 10" />
								<line x1="12" y1="15" x2="12" y2="3" />
							</svg>
						</div>
						<div>
							<div style={{ fontSize: 13, fontWeight: 500 }}>数据导出</div>
							<div className="text-xs text-muted">导出CSV文件</div>
						</div>
					</div>
					<div className="quick-item" onClick={() => onQuickAction("/")}>
						<div
							className="quick-icon"
							style={{
								background: "var(--warning-rgba)",
								color: "var(--warning)",
							}}
						>
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								strokeWidth="2"
							>
								<circle cx="11" cy="11" r="8" />
								<path d="M21 21l-4.35-4.35" />
							</svg>
						</div>
						<div>
							<div style={{ fontSize: 13, fontWeight: 500 }}>IP反查</div>
							<div className="text-xs text-muted">按虚拟IP查用户</div>
						</div>
					</div>
					<div
						className="quick-item"
						onClick={() => onQuickAction("/settings")}
					>
						<div
							className="quick-icon"
							style={{
								background: "var(--accent-rgba)",
								color: "var(--accent-light)",
							}}
						>
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								strokeWidth="2"
							>
								<line x1="18" y1="20" x2="18" y2="10" />
								<line x1="12" y1="20" x2="12" y2="4" />
								<line x1="6" y1="20" x2="6" y2="14" />
							</svg>
						</div>
						<div>
							<div style={{ fontSize: 13, fontWeight: 500 }}>系统状态</div>
							<div className="text-xs text-muted">查看运行状态</div>
						</div>
					</div>
				</div>
			</div>
		</>
	);
}
