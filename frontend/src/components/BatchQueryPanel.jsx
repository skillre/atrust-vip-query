import { useState } from "react";
import API_BASE from "../config";

export default function BatchQueryPanel() {
	const [input, setInput] = useState("");
	const [fuzzy, setFuzzy] = useState(false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState("");
	const [matches, setMatches] = useState(null);

	// 将输入按换行/逗号/分号/空格拆分为名称数组（去空去重）
	function parseNames(text) {
		const raw = text
			.split(/[\n,;，；\s]+/)
			.map((s) => s.trim())
			.filter(Boolean);
		return Array.from(new Set(raw));
	}

	const names = parseNames(input);

	async function doBatchQuery() {
		if (names.length === 0) {
			setError("请输入至少一个用户名或显示名");
			return;
		}
		if (names.length > 500) {
			setError(`单次批量查询不能超过 500 个，当前 ${names.length} 个`);
			return;
		}
		setLoading(true);
		setError("");
		setMatches(null);
		try {
			const resp = await fetch(`${API_BASE}/vip/query/batch`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ names, fuzzy }),
			});
			const data = await resp.json();
			if (data.code === 0 && data.data) {
				setMatches(data.data.matches || []);
			} else {
				setError(data.message || "查询失败");
			}
		} catch {
			setError("网络错误，请检查后端服务");
		} finally {
			setLoading(false);
		}
	}

	function exportCsv() {
		if (!matches || matches.length === 0) return;
		const header = ["用户名", "显示名", "手机号", "当前虚拟IP", "真实IP", "最近时间"];
		const rows = matches.map((m) => {
			const v = m.history_vip;
			return [
				m.user_name,
				m.display_name || "",
				m.phone || "",
				v ? v.virtual_ip : "",
				v && v.real_ip ? v.real_ip : "",
				v && v.timestamp ? new Date(v.timestamp).toLocaleString("zh-CN") : "",
			];
		});
		const csv = [header, ...rows]
			.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
			.join("\n");
		const blob = new Blob(["\uFEFF" + csv], {
			type: "text/csv;charset=utf-8;",
		});
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `批量查询结果_${new Date().toISOString().slice(0, 10)}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

	return (
		<div className="main-content">
			<div className="main-left">
				<div className="card">
					<div className="card-header">
						<span className="card-title">批量查询虚拟IP</span>
						<span className="text-xs text-muted">
							{names.length > 0
								? `已识别 ${names.length} 个名称`
								: "支持换行/逗号/空格分隔"}
						</span>
					</div>
					<div className="card-body">
						<textarea
							value={input}
							onChange={(e) => setInput(e.target.value)}
							placeholder={
								"每行一个用户名/显示名/手机号，也可用逗号、空格分隔，例如：\nzhangsan\nlisi\n13800138000"
							}
							rows={8}
							style={{
								width: "100%",
								padding: 12,
								borderRadius: 8,
								border: "1px solid var(--border)",
								background: "var(--bg-input, var(--bg-secondary))",
								color: "var(--text-primary)",
								fontFamily: "var(--font-mono)",
								fontSize: 14,
								resize: "vertical",
								boxSizing: "border-box",
							}}
						/>
						<div
							style={{
								display: "flex",
								alignItems: "center",
								gap: 16,
								marginTop: 12,
								flexWrap: "wrap",
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
								模糊匹配（每个关键词可命中多个用户）
							</label>
							<button
								className="search-btn"
								onClick={doBatchQuery}
								disabled={loading}
								style={{ marginLeft: "auto" }}
							>
								{loading ? "查询中..." : "批量查询"}
							</button>
						</div>
						{error && (
							<p style={{ color: "var(--error)", marginTop: 12 }}>{error}</p>
						)}
					</div>
				</div>

				{matches && (
					<div className="card">
						<div className="card-header">
							<span className="card-title">查询结果</span>
							<span style={{ display: "flex", alignItems: "center", gap: 12 }}>
								<span className="text-xs text-muted">
									共 {matches.length} 条
								</span>
								{matches.length > 0 && (
									<span
										className="text-xs"
										style={{ color: "var(--accent)", cursor: "pointer" }}
										onClick={exportCsv}
									>
										导出 CSV
									</span>
								)}
							</span>
						</div>
						{matches.length === 0 ? (
							<div className="card-body text-center" style={{ padding: 40 }}>
								<p className="text-muted">未找到匹配用户</p>
							</div>
						) : (
							<>
								<div className="table-header">
									<span style={{ width: 140 }}>用户名</span>
									<span style={{ width: 130 }}>显示名</span>
									<span style={{ width: 130 }}>手机号</span>
									<span style={{ width: 140 }}>当前虚拟IP</span>
									<span style={{ width: 140 }}>真实IP</span>
									<span style={{ width: 170 }}>最近时间</span>
								</div>
								{matches.map((m, idx) => {
									const v = m.history_vip;
									return (
										<div className="table-row" key={m.user_name || idx}>
											<span style={{ width: 140, fontWeight: 500 }}>
												{m.user_name}
											</span>
											<span className="text-secondary" style={{ width: 130 }}>
												{m.display_name || "-"}
											</span>
											<span className="text-secondary" style={{ width: 130 }}>
												{m.phone || "-"}
											</span>
											<span
												className="col-accent"
												style={{ width: 140, fontFamily: "var(--font-mono)" }}
											>
												{v ? v.virtual_ip : "-"}
											</span>
											<span
												className="text-secondary"
												style={{ width: 140, fontFamily: "var(--font-mono)" }}
											>
												{v && v.real_ip ? v.real_ip : "-"}
											</span>
											<span
												className="text-muted"
												style={{ width: 170, fontFamily: "var(--font-mono)" }}
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
				)}
			</div>
		</div>
	);
}
