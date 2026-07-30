import { useState, useEffect } from "react";
import API_BASE from "../config";

export default function StatsRow() {
	const [stats, setStats] = useState({
		online_users: 0,
		today_queries: 0,
		vip_pool_size: 0,
		last_sync: "",
	});

	useEffect(() => {
		fetchStats();
	}, []);

	async function fetchStats() {
		try {
			const resp = await fetch(`${API_BASE}/dashboard/stats`);
			const data = await resp.json();
			if (data.code === 0 && data.data) {
				setStats(data.data);
			}
		} catch {
			// 使用默认值
		}
	}

	function formatSyncTime(ts) {
		if (!ts) return "暂无数据";
		try {
			const d = new Date(ts);
			const now = new Date();
			const diff = Math.floor((now - d) / 60000);
			if (diff < 1) return "刚刚";
			if (diff < 60) return `${diff}分钟前`;
			if (diff < 1440) return `${Math.floor(diff / 60)}小时前`;
			return `${Math.floor(diff / 1440)}天前`;
		} catch {
			return ts;
		}
	}

	return (
		<div className="stats-row">
			<div className="stat-card">
				<div className="stat-icon blue">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						strokeWidth="2"
					>
						<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
						<circle cx="9" cy="7" r="4" />
						<path d="M23 21v-2a4 4 0 0 0-3-3.87" />
						<path d="M16 3.13a4 4 0 0 1 0 7.75" />
					</svg>
				</div>
				<div>
					<div className="stat-value">
						{stats.online_users.toLocaleString()}
					</div>
					<div className="stat-label">在线用户</div>
				</div>
			</div>

			<div className="stat-card">
				<div className="stat-icon blue">
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
					<div className="stat-value">
						{stats.today_queries.toLocaleString()}
					</div>
					<div className="stat-label">今日查询</div>
				</div>
			</div>

			<div className="stat-card">
				<div className="stat-icon blue">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						strokeWidth="2"
					>
						<rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
						<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
					</svg>
				</div>
				<div>
					<div className="stat-value">
						{stats.vip_pool_size.toLocaleString()}
					</div>
					<div className="stat-label">虚拟IP池</div>
				</div>
			</div>

			<div className="stat-card">
				<div className="stat-icon yellow">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						strokeWidth="2"
					>
						<circle cx="12" cy="12" r="10" />
						<polyline points="12 6 12 12 16 14" />
					</svg>
				</div>
				<div>
					<div className="stat-value" style={{ fontSize: "16px" }}>
						{formatSyncTime(stats.last_sync)}
					</div>
					<div className="stat-label">数据同步</div>
				</div>
			</div>
		</div>
	);
}
