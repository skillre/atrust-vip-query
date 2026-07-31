import { useState, useEffect } from "react";
import API_BASE from "../config";

export default function SettingsPage() {
	const [config, setConfig] = useState(null);
	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [syslogStatus, setSyslogStatus] = useState(null);
	const [trend, setTrend] = useState({ running: false, points: [] });

	useEffect(() => {
		fetchConfig();
		fetchStatus();
		// 轮询刷新：状态 5s，趋势 2s（组件卸载时清理）
		const statusTimer = setInterval(fetchStatus, 5000);
		const trendTimer = setInterval(fetchTrend, 2000);
		return () => {
			clearInterval(statusTimer);
			clearInterval(trendTimer);
		};
	}, []);

	async function fetchConfig() {
		try {
			const resp = await fetch(`${API_BASE}/system/config`);
			const data = await resp.json();
			if (data.code === 0 && data.data) {
				setConfig(data.data);
			}
		} catch {
		} finally {
			setLoading(false);
		}
	}

	async function fetchStatus() {
		try {
			const resp = await fetch(`${API_BASE}/system/status-full`);
			const data = await resp.json();
			if (data.code === 0 && data.data) {
				setSyslogStatus(data.data);
			}
		} catch {}
	}

	async function fetchTrend() {
		try {
			const resp = await fetch(`${API_BASE}/system/syslog/trend?minutes=10`);
			const data = await resp.json();
			if (data.code === 0 && data.data) {
				setTrend(data.data);
			}
		} catch {}
	}

	function updateField(field, value) {
		setConfig((prev) => ({ ...prev, [field]: value }));
	}

	async function handleSave() {
		setSaving(true);
		try {
			const resp = await fetch(`${API_BASE}/system/config`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(config),
			});
			const data = await resp.json();
			if (data.code === 0) {
				alert("配置已保存");
			} else {
				alert(data.message || "保存失败");
			}
		} catch {
			alert("保存失败");
		} finally {
			setSaving(false);
		}
	}

	async function handleTestAtrust() {
		try {
			const resp = await fetch(`${API_BASE}/system/test-atrust`, {
				method: "POST",
			});
			const data = await resp.json();
			alert(data.code === 0 ? "连接成功" : data.message || "连接失败");
		} catch {
			alert("测试失败");
		}
	}

	async function handleRestartSyslog() {
		try {
			const resp = await fetch(`${API_BASE}/system/syslog/restart`, {
				method: "POST",
			});
			const data = await resp.json();
			alert(data.code === 0 ? "Syslog 已重启" : data.message || "重启失败");
			fetchStatus();
		} catch {
			alert("重启失败");
		}
	}

	if (loading)
		return (
			<div
				className="text-secondary"
				style={{ padding: 40, textAlign: "center" }}
			>
				加载中...
			</div>
		);
	if (!config)
		return (
			<div
				className="text-secondary"
				style={{ padding: 40, textAlign: "center" }}
			>
				加载配置失败
			</div>
		);

	return (
		<div>
			<div className="page-header">
				<div>
					<h1 className="page-title">系统配置</h1>
					<p className="page-subtitle">管理系统运行参数，修改后点击保存生效</p>
				</div>
				<div style={{ display: "flex", gap: 12 }}>
					<button className="btn btn-secondary" onClick={fetchConfig}>
						恢复默认
					</button>
					<button
						className="btn btn-primary"
						onClick={handleSave}
						disabled={saving}
					>
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							strokeWidth="2"
							width="14"
							height="14"
						>
							<polyline points="20 6 9 17 4 12" />
						</svg>
						{saving ? "保存中..." : "保存所有配置"}
					</button>
				</div>
			</div>

			<div className="settings-grid">
				<div className="settings-col">
					{/* 运行模式 */}
					<div className="card">
						<div className="card-header">
							<div className="card-title">
								<svg
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--accent)"
									strokeWidth="2"
									width="16"
									height="16"
								>
									<polyline points="16 3 21 3 21 8" />
									<line x1="4" y1="20" x2="21" y2="3" />
									<polyline points="21 16 21 21 16 21" />
									<line x1="15" y1="15" x2="21" y2="21" />
									<line x1="4" y1="4" x2="9" y2="9" />
								</svg>
								运行模式
							</div>
						</div>
						<div
							className="card-body"
							style={{ display: "flex", flexDirection: "column", gap: 12 }}
						>
							<div style={{ display: "flex", gap: 8 }}>
								<div
									style={{
										flex: 1,
										padding: 12,
										borderRadius: 8,
										cursor: "pointer",
										textAlign: "center",
										background:
											config.mode === "import"
												? "var(--accent)"
												: "var(--bg-input)",
										border:
											config.mode === "import"
												? "none"
												: "1px solid var(--border)",
										color:
											config.mode === "import"
												? "#fff"
												: "var(--text-secondary)",
									}}
									onClick={() => updateField("mode", "import")}
								>
									<div style={{ fontWeight: 600, fontSize: 12 }}>导入模式</div>
									<div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>
										上传日志文件
									</div>
								</div>
								<div
									style={{
										flex: 1,
										padding: 12,
										borderRadius: 8,
										cursor: "pointer",
										textAlign: "center",
										background:
											config.mode === "realtime"
												? "var(--accent)"
												: "var(--bg-input)",
										border:
											config.mode === "realtime"
												? "none"
												: "1px solid var(--border)",
										color:
											config.mode === "realtime"
												? "#fff"
												: "var(--text-secondary)",
									}}
									onClick={() => updateField("mode", "realtime")}
								>
									<div style={{ fontWeight: 600, fontSize: 12 }}>实时模式</div>
									<div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>
										连接 aTrust 设备
									</div>
								</div>
							</div>
							<p className="text-xs text-muted">
								导入模式：通过Web界面上传日志文件，无需网络连接
								<br />
								实时模式：实时连接aTrust设备，自动采集数据（需配置设备信息）
							</p>
						</div>
					</div>

					{/* aTrust 设备配置 */}
					<div className="card">
						<div className="card-header">
							<div className="card-title">
								<svg
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--accent)"
									strokeWidth="2"
									width="16"
									height="16"
								>
									<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
									<polyline points="9 22 9 12 15 12 15 22" />
								</svg>
								aTrust 设备配置
							</div>
							<button
								className="btn btn-secondary"
								style={{ padding: "4px 10px", fontSize: 11 }}
								onClick={handleTestAtrust}
							>
								测试连接
							</button>
						</div>
						<div
							className="card-body"
							style={{ display: "flex", flexDirection: "column", gap: 12 }}
						>
							<FormField
								label="控制台地址"
								value={config.atrust_host}
								onChange={(v) => updateField("atrust_host", v)}
								placeholder="https://"
							/>
							<FormField
								label="API ID"
								value={config.atrust_api_id}
								onChange={(v) => updateField("atrust_api_id", v)}
								placeholder="从控制台获取"
							/>
							<FormField
								label="API Key"
								value={config.atrust_api_key}
								onChange={(v) => updateField("atrust_api_key", v)}
								type="password"
							/>
							<FormField
								label="API 超时（秒）"
								value={config.atrust_timeout}
								onChange={(v) =>
									updateField("atrust_timeout", parseInt(v) || 10)
								}
								style={{ width: 200 }}
							/>
						</div>
					</div>

					{/* 数据库配置 */}
					<div className="card">
						<div className="card-header">
							<div className="card-title">
								<svg
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--accent)"
									strokeWidth="2"
									width="16"
									height="16"
								>
									<ellipse cx="12" cy="5" rx="9" ry="3" />
									<path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
									<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
								</svg>
								数据库配置
							</div>
						</div>
						<div
							className="card-body"
							style={{ display: "flex", flexDirection: "column", gap: 12 }}
						>
							<FormField
								label="数据库路径"
								value={config.db_path}
								onChange={(v) => updateField("db_path", v)}
							/>
							<div style={{ display: "flex", gap: 12 }}>
								<FormField
									label="数据保留（天）"
									value={config.db_retention_days}
									onChange={(v) =>
										updateField("db_retention_days", parseInt(v) || 90)
									}
								/>
								<FormField
									label="批量写入"
									value={config.db_batch_size}
									onChange={(v) =>
										updateField("db_batch_size", parseInt(v) || 5000)
									}
								/>
								<FormField
									label="刷盘间隔"
									value={config.db_flush_interval}
									onChange={(v) =>
										updateField("db_flush_interval", parseFloat(v) || 5.0)
									}
								/>
							</div>
						</div>
					</div>
				</div>

				<div className="settings-col">
					{/* Syslog 接收器 */}
					<div className="card">
						<div className="card-header">
							<div className="card-title">
								<svg
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--success)"
									strokeWidth="2"
									width="16"
									height="16"
								>
									<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
									<path d="M19 10v2a7 7 0 0 1-14 0v-2" />
									<line x1="12" y1="19" x2="12" y2="23" />
									<line x1="8" y1="23" x2="16" y2="23" />
								</svg>
								Syslog 接收器
							</div>
							<div style={{ display: "flex", alignItems: "center", gap: 8 }}>
								{syslogStatus?.syslog_status === "running" && (
									<span className="badge badge-online">
										<span
											className="status-dot"
											style={{ width: 6, height: 6 }}
										/>{" "}
										运行中
									</span>
								)}
								<button
									className="btn btn-secondary"
									style={{ padding: "4px 10px", fontSize: 11 }}
									onClick={handleRestartSyslog}
								>
									重启
								</button>
							</div>
						</div>
						<div
							className="card-body"
							style={{ display: "flex", flexDirection: "column", gap: 12 }}
						>
							<div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
								<div style={{ flex: 1 }}>
									<div
										style={{
											display: "flex",
											justifyContent: "space-between",
											alignItems: "center",
											padding: "10px 12px",
											background: "var(--bg-input)",
											borderRadius: 6,
										}}
									>
										<span className="text-secondary" style={{ fontSize: 12 }}>
											启用接收器
										</span>
										<div
											className={`toggle ${config.syslog_enabled ? "on" : ""}`}
											onClick={() =>
												updateField("syslog_enabled", !config.syslog_enabled)
											}
										>
											<div className="toggle-knob" />
										</div>
									</div>
								</div>
								<FormField
									label="协议"
									value={config.syslog_protocol}
									onChange={(v) => updateField("syslog_protocol", v)}
									style={{ width: 100 }}
								/>
							</div>
							<div style={{ display: "flex", gap: 12 }}>
								<FormField
									label="监听地址"
									value={config.syslog_host}
									onChange={(v) => updateField("syslog_host", v)}
								/>
								<FormField
									label="端口"
									value={config.syslog_port}
									onChange={(v) =>
										updateField("syslog_port", parseInt(v) || 514)
									}
									style={{ width: 120 }}
								/>
							</div>
							<div style={{ display: "flex", gap: 12 }}>
								<FormField
									label="线程数"
									value={config.syslog_workers}
									onChange={(v) =>
										updateField("syslog_workers", parseInt(v) || 4)
									}
								/>
								<FormField
									label="批量大小"
									value={config.syslog_batch_size}
									onChange={(v) =>
										updateField("syslog_batch_size", parseInt(v) || 5000)
									}
								/>
								<FormField
									label="刷盘间隔"
									value={config.syslog_flush_interval}
									onChange={(v) =>
										updateField("syslog_flush_interval", parseFloat(v) || 5.0)
									}
								/>
							</div>
						</div>
					</div>

					{/* API 服务 */}
					<div className="card">
						<div className="card-header">
							<div className="card-title">
								<svg
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--accent-light)"
									strokeWidth="2"
									width="16"
									height="16"
								>
									<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
								</svg>
								API 服务
							</div>
						</div>
						<div
							className="card-body"
							style={{ display: "flex", flexDirection: "column", gap: 12 }}
						>
							<div style={{ display: "flex", gap: 12 }}>
								<FormField
									label="监听地址"
									value={config.api_host}
									onChange={(v) => updateField("api_host", v)}
								/>
								<FormField
									label="端口"
									value={config.api_port}
									onChange={(v) => updateField("api_port", parseInt(v) || 8000)}
									style={{ width: 100 }}
								/>
							</div>
							<div
								style={{
									display: "flex",
									justifyContent: "space-between",
									alignItems: "center",
									padding: "10px 12px",
									background: "var(--bg-input)",
									borderRadius: 6,
								}}
							>
								<span className="text-muted" style={{ fontSize: 11 }}>
									调试
								</span>
								<div
									className={`toggle ${config.api_debug ? "on" : ""}`}
									onClick={() => updateField("api_debug", !config.api_debug)}
								>
									<div className="toggle-knob" />
								</div>
							</div>
						</div>
					</div>

					{/* 日志配置 */}
					<div className="card">
						<div className="card-header">
							<div className="card-title">
								<svg
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--warning)"
									strokeWidth="2"
									width="16"
									height="16"
								>
									<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
									<polyline points="14 2 14 8 20 8" />
									<line x1="16" y1="13" x2="8" y2="13" />
									<line x1="16" y1="17" x2="8" y2="17" />
								</svg>
								日志配置
							</div>
						</div>
						<div
							className="card-body"
							style={{ display: "flex", flexDirection: "column", gap: 12 }}
						>
							<div style={{ display: "flex", gap: 12 }}>
								<FormField
									label="日志级别"
									value={config.log_level}
									onChange={(v) => updateField("log_level", v)}
									style={{ width: 120 }}
								/>
								<FormField
									label="日志文件"
									value={config.log_file}
									onChange={(v) => updateField("log_file", v)}
								/>
							</div>
							<div style={{ display: "flex", gap: 12 }}>
								<FormField
									label="最大MB"
									value={config.log_max_size}
									onChange={(v) =>
										updateField("log_max_size", parseInt(v) || 10)
									}
									style={{ width: 80 }}
								/>
								<FormField
									label="备份数"
									value={config.log_backup_count}
									onChange={(v) =>
										updateField("log_backup_count", parseInt(v) || 5)
									}
									style={{ width: 80 }}
								/>
							</div>
						</div>
					</div>
				</div>
			</div>

			{/* 系统状态区域 */}
			{syslogStatus && (
				<div style={{ marginTop: 32 }}>
					<h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>
						系统状态
					</h2>
					<div className="health-grid">
						<HealthCard
							label="系统状态"
							value={syslogStatus.status === "healthy" ? "正常" : "异常"}
							sub={`运行时间: ${syslogStatus.uptime || "未知"}`}
							ok={syslogStatus.status === "healthy"}
						/>
						<HealthCard
							label="数据库"
							value={
								syslogStatus.database_status === "connected" ? "已连接" : "断开"
							}
							sub="SQLite"
							ok={syslogStatus.database_status === "connected"}
						/>
						<HealthCard
							label="Syslog 接收器"
							value={
								syslogStatus.syslog_status === "running" ? "运行中" : "已停止"
							}
							sub={`端口 ${config.syslog_port} (${config.syslog_protocol?.toUpperCase()})`}
							ok={syslogStatus.syslog_status === "running"}
						/>
						<HealthCard
							label="aTrust API"
							value={
								syslogStatus.atrust_api_status === "disabled"
									? "未启用"
									: "已连接"
							}
							sub="导入模式运行"
							ok={false}
							disabled={true}
						/>
					</div>

					{/* 实时接收趋势图 */}
					<div style={{ marginTop: 16 }}>
						<div className="card">
							<div className="card-header">
								<div className="card-title">实时接收趋势（近 10 分钟）</div>
								{syslogStatus.syslog_status === "running" && (
									<span className="badge badge-online">
										<span
											className="status-dot"
											style={{ width: 6, height: 6 }}
										/>{" "}
										{trend.points?.length
											? `${trend.points[trend.points.length - 1].received} 条/秒`
											: "等待数据"}
									</span>
								)}
							</div>
							<div className="card-body">
								<TrendChart points={trend.points || []} />
								<div
									style={{
										display: "flex",
										gap: 16,
										marginTop: 10,
										fontSize: 12,
										color: "var(--text-secondary)",
									}}
								>
									<span
										style={{ display: "flex", alignItems: "center", gap: 6 }}
									>
										<span
											style={{
												width: 16,
												height: 3,
												background: "var(--accent)",
												display: "inline-block",
											}}
										/>
										接收
									</span>
									<span
										style={{ display: "flex", alignItems: "center", gap: 6 }}
									>
										<span
											style={{
												width: 16,
												height: 3,
												background: "var(--success)",
												display: "inline-block",
											}}
										/>
										解析成功
									</span>
									<span
										style={{ display: "flex", alignItems: "center", gap: 6 }}
									>
										<span
											style={{
												width: 16,
												height: 3,
												background: "var(--error)",
												display: "inline-block",
											}}
										/>
										解析失败
									</span>
								</div>
							</div>
						</div>
					</div>

					<div
						style={{
							display: "grid",
							gridTemplateColumns: "1fr 1fr",
							gap: 16,
							marginTop: 16,
						}}
					>
						<div className="card">
							<div className="card-header">
								<div className="card-title">数据库统计</div>
							</div>
							<div
								className="card-body"
								style={{ display: "flex", flexDirection: "column", gap: 8 }}
							>
								<StatItem
									label="用户总数"
									value={
										syslogStatus.db_stats?.user_count?.toLocaleString() || "0"
									}
								/>
								<StatItem
									label="虚拟IP记录"
									value={
										syslogStatus.db_stats?.record_count?.toLocaleString() || "0"
									}
								/>
								<StatItem
									label="今日导入"
									value={
										syslogStatus.db_stats?.today_imports?.toLocaleString() ||
										"0"
									}
								/>
								<StatItem
									label="数据库大小"
									value={`${syslogStatus.db_stats?.db_size_mb || 0} MB`}
								/>
							</div>
						</div>
						<div className="card">
							<div className="card-header">
								<div className="card-title">Syslog 接收器性能</div>
							</div>
							<div
								className="card-body"
								style={{ display: "flex", flexDirection: "column", gap: 8 }}
							>
								<div className="metric-row">
									<span className="metric-label">监听状态</span>
									<span className="metric-value">
										{syslogStatus.syslog_stats?.listen_address || "未运行"}
									</span>
								</div>
								<div className="metric-row">
									<span className="metric-label">累计接收</span>
									<span className="metric-value">
										{syslogStatus.syslog_stats?.total_received?.toLocaleString() ||
											"0"}{" "}
										条
									</span>
								</div>
								<div className="metric-row">
									<span className="metric-label">接收速率</span>
									<span className="metric-value">
										{syslogStatus.syslog_stats?.rate_per_sec ?? 0} 条/秒
									</span>
								</div>
								<div className="metric-row">
									<span className="metric-label">解析成功</span>
									<span className="metric-value">
										{syslogStatus.syslog_stats?.parse_success?.toLocaleString() ||
											"0"}{" "}
										条
									</span>
								</div>
								<div className="metric-row">
									<span className="metric-label">解析失败</span>
									<span className="metric-value">
										{syslogStatus.syslog_stats?.parse_failed?.toLocaleString() ||
											"0"}{" "}
										条
									</span>
								</div>
								<div className="metric-row">
									<span className="metric-label">写入成功</span>
									<span className="metric-value">
										{syslogStatus.syslog_stats?.written?.toLocaleString() ||
											"0"}{" "}
										条
									</span>
								</div>
								<div className="metric-row">
									<span className="metric-label">队列深度</span>
									<span className="metric-value">
										解析 {syslogStatus.syslog_stats?.parse_queue ?? 0} / 写入{" "}
										{syslogStatus.syslog_stats?.write_queue ?? 0}
									</span>
								</div>
								<div className="metric-row">
									<span className="metric-label">批处理大小</span>
									<span className="metric-value">
										{syslogStatus.syslog_stats?.batch_size ||
											config.syslog_batch_size}{" "}
										条
									</span>
								</div>
								{syslogStatus.syslog_stats?.last_raw_sample && (
									<div style={{ marginTop: 4 }}>
										<div className="metric-label" style={{ marginBottom: 4 }}>
											最近原始日志
										</div>
										<pre
											style={{
												background: "var(--bg-input)",
												borderRadius: 6,
												padding: 8,
												fontSize: 11,
												whiteSpace: "pre-wrap",
												wordBreak: "break-all",
												maxHeight: 120,
												overflow: "auto",
												margin: 0,
												color: "var(--text-secondary)",
											}}
										>
											{syslogStatus.syslog_stats.last_raw_sample}
										</pre>
									</div>
								)}
								{syslogStatus.syslog_stats?.last_error_sample && (
									<div style={{ marginTop: 4 }}>
										<div className="metric-label" style={{ marginBottom: 4 }}>
											最近解析失败日志
										</div>
										<pre
											style={{
												background: "var(--error-rgba)",
												borderRadius: 6,
												padding: 8,
												fontSize: 11,
												whiteSpace: "pre-wrap",
												wordBreak: "break-all",
												maxHeight: 120,
												overflow: "auto",
												margin: 0,
												color: "var(--error)",
											}}
										>
											{syslogStatus.syslog_stats.last_error_sample}
										</pre>
									</div>
								)}
							</div>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}

function TrendChart({ points, height = 160 }) {
	if (!points || points.length < 2) {
		return (
			<div
				className="text-muted"
				style={{ padding: 24, textAlign: "center", fontSize: 12 }}
			>
				暂无数据 — 等待 aTrust 设备发送 Syslog 日志…
			</div>
		);
	}

	const W = 800;
	const H = height;
	const PAD = 10;
	const maxV = Math.max(
		1,
		...points.map((p) =>
			Math.max(p.received || 0, p.parsed || 0, p.errors || 0),
		),
	);
	const x = (i) => PAD + (i * (W - PAD * 2)) / (points.length - 1);
	const y = (v) => H - PAD - (v / maxV) * (H - PAD * 2);
	const line = (key) =>
		points
			.map(
				(p, i) =>
					`${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p[key] || 0).toFixed(1)}`,
			)
			.join(" ");

	return (
		<svg
			viewBox={`0 0 ${W} ${H}`}
			style={{ width: "100%", height: "auto", display: "block" }}
		>
			<path
				d={line("received")}
				fill="none"
				stroke="var(--accent)"
				strokeWidth="1.5"
			/>
			<path
				d={line("parsed")}
				fill="none"
				stroke="var(--success)"
				strokeWidth="1.5"
			/>
			<path
				d={line("errors")}
				fill="none"
				stroke="var(--error)"
				strokeWidth="1.5"
			/>
		</svg>
	);
}

function FormField({
	label,
	value,
	onChange,
	type = "text",
	placeholder,
	style,
}) {
	return (
		<div className="form-field" style={style}>
			<label className="form-label">{label}</label>
			<input
				className="form-input"
				type={type}
				value={value ?? ""}
				onChange={(e) => onChange(e.target.value)}
				placeholder={placeholder}
			/>
		</div>
	);
}

function HealthCard({ label, value, sub, ok, disabled }) {
	return (
		<div className="health-card">
			<div className="health-card-header">
				<span className="health-card-label">{label}</span>
				<span
					className="status-dot"
					style={{
						width: 8,
						height: 8,
						background: disabled
							? "var(--text-muted)"
							: ok
								? "var(--success)"
								: "var(--error)",
					}}
				/>
			</div>
			<div className="health-card-value">{value}</div>
			<div className="health-card-sub">{sub}</div>
		</div>
	);
}

function StatItem({ label, value }) {
	return (
		<div className="stat-list-item">
			<div className="stat-list-icon">
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					strokeWidth="2"
				>
					<rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
					<line x1="3" y1="9" x2="21" y2="9" />
					<line x1="9" y1="21" x2="9" y2="9" />
				</svg>
			</div>
			<div style={{ flex: 1 }}>
				<div className="stat-list-label">{label}</div>
				<div className="stat-list-value">{value}</div>
			</div>
		</div>
	);
}
