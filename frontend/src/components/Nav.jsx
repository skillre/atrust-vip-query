import { Link, useLocation } from "react-router-dom";

const navItems = [
	{ path: "/", label: "查询" },
	{ path: "/history", label: "历史记录" },
	{ path: "/import", label: "数据导入" },
	{ path: "/export", label: "数据导出" },
	{ path: "/settings", label: "系统配置" },
];

export default function Nav({ systemStatus }) {
	const location = useLocation();

	return (
		<header className="topnav">
			<div className="container topnav-inner">
				<Link to="/" className="logo" style={{ textDecoration: "none" }}>
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						strokeWidth="1.6"
					>
						<path d="M12 2l-9 5v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12v-5l-9-5z" />
					</svg>
					<span>aTrust</span>
					<span className="logo-sub">虚拟IP查询</span>
				</Link>
				<nav className="nav-links">
					{navItems.map((item) => (
						<Link
							key={item.path}
							to={item.path}
							className={`nav-link ${location.pathname === item.path ? "active" : ""}`}
						>
							{item.label}
						</Link>
					))}
				</nav>
				<div
					className={`status-badge ${systemStatus === "healthy" ? "healthy" : systemStatus === "checking" ? "checking" : "error"}`}
				>
					<span className="status-dot" />
					{systemStatus === "healthy"
						? "系统正常"
						: systemStatus === "checking"
							? "检查中..."
							: "未连接"}
				</div>
			</div>
		</header>
	);
}
