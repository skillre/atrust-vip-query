import { useState, useEffect } from "react";
import API_BASE from "../config";

export default function QueryPanel({ queryInput, queryType }) {
	const [loading, setLoading] = useState(false);
	const [result, setResult] = useState(null);
	const [error, setError] = useState(null);

	useEffect(() => {
		if (queryInput && queryType === "user") {
			performSearch(queryInput);
		}
	}, [queryInput, queryType]);

	async function performSearch(name) {
		setLoading(true);
		setError(null);
		setResult(null);

		try {
			const resp = await fetch(
				`${API_BASE}/vip/query?name=${encodeURIComponent(name)}`,
			);
			const data = await resp.json();

			if (data.code === 0 && data.data) {
				setResult(data.data);
			} else {
				setError(data.message || "未找到用户");
			}
		} catch (err) {
			setError("无法连接到 API 服务，请确保后端已启动");
		} finally {
			setLoading(false);
		}
	}

	if (loading) {
		return (
			<div className="tab-panel active">
				<div className="text-center mt-6">
					<div className="spinner" style={{ margin: "0 auto" }}></div>
					<p className="mt-4" style={{ color: "var(--muted)" }}>
						正在查询...
					</p>
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="tab-panel active">
				<div className="empty-state">
					<svg
						className="empty-icon"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						strokeWidth="1.5"
					>
						<circle cx="12" cy="12" r="10" />
						<path d="M15 9l-6 6M9 9l6 6" />
					</svg>
					<div className="empty-title">{error}</div>
					<div className="empty-desc">请检查输入是否正确，或尝试其他搜索词</div>
				</div>
			</div>
		);
	}

	if (!result) {
		return (
			<div className="tab-panel active">
				<div id="query-results">
					<div className="empty-state">
						<svg
							className="empty-icon"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							strokeWidth="1.5"
						>
							<circle cx="11" cy="11" r="8" />
							<path d="M21 21l-4.35-4.35" />
						</svg>
						<div className="empty-title">输入查询条件开始搜索</div>
						<div className="empty-desc">
							在上方搜索框中输入用户名或虚拟IP地址，快速获取查询结果
						</div>
					</div>
				</div>
			</div>
		);
	}

	const isOnline = result.is_online;
	const onlineVips = result.online_vips || [];
	const historyVip = result.history_vip;

	return (
		<div className="tab-panel active">
			<div className="result-card">
				<div className="result-header">
					<div className="result-user">
						<span className="result-user-name">{result.user_name}</span>
						{result.display_name && (
							<span className="result-user-display">
								({result.display_name})
							</span>
						)}
					</div>
					<span
						className={`badge ${isOnline ? "badge-online" : "badge-offline"}`}
					>
						<span className="badge-dot"></span>
						{isOnline ? "在线" : "离线"}
					</span>
				</div>
				<div className="result-body">
					{onlineVips.length > 0 && (
						<div className="result-section">
							<div className="result-section-title">
								<svg
									width="14"
									height="14"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
								>
									<circle cx="12" cy="12" r="10" />
									<path d="M8 12l3 3 5-5" />
								</svg>
								在线虚拟IP
							</div>
							{onlineVips.map((vip, i) => (
								<div className="vip-item" key={i}>
									<span className="vip-ip">{vip.ip}</span>
									{vip.real_ip && (
										<span className="vip-meta">真实IP: {vip.real_ip}</span>
									)}
									{vip.last_login_time && (
										<span className="vip-meta">
											登录: {vip.last_login_time}
										</span>
									)}
								</div>
							))}
						</div>
					)}

					{historyVip && (
						<div className="result-section">
							<div className="result-section-title">
								<svg
									width="14"
									height="14"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
								>
									<circle cx="12" cy="12" r="10" />
									<polyline points="12,6 12,12 16,14" />
								</svg>
								最近历史记录
							</div>
							<div className="vip-item">
								<span className="vip-ip">{historyVip.virtual_ip}</span>
								{historyVip.real_ip && (
									<span className="vip-meta">真实IP: {historyVip.real_ip}</span>
								)}
								<span className="vip-meta">{historyVip.timestamp}</span>
								<span className="badge badge-info">
									{historyVip.event_type}
								</span>
							</div>
						</div>
					)}

					{!isOnline && onlineVips.length === 0 && !historyVip && (
						<div className="empty-state" style={{ padding: "32px" }}>
							<div className="empty-desc">暂无虚拟IP记录</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
