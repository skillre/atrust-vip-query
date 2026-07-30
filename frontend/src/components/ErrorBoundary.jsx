import { Component } from "react";

export default class ErrorBoundary extends Component {
	constructor(props) {
		super(props);
		this.state = { hasError: false, error: null };
	}

	static getDerivedStateFromError(error) {
		return { hasError: true, error };
	}

	componentDidCatch(error, errorInfo) {
		console.error("组件错误:", error, errorInfo);
	}

	render() {
		if (this.state.hasError) {
			return (
				<div
					style={{
						padding: "48px 24px",
						textAlign: "center",
						color: "var(--text)",
						fontFamily: "var(--font-sans)",
					}}
				>
					<svg
						width="48"
						height="48"
						viewBox="0 0 24 24"
						fill="none"
						stroke="var(--danger)"
						strokeWidth="1.5"
						style={{ marginBottom: "16px" }}
					>
						<circle cx="12" cy="12" r="10" />
						<path d="M15 9l-6 6M9 9l6 6" />
					</svg>
					<h2
						style={{
							fontSize: "1.25rem",
							fontWeight: 600,
							marginBottom: "8px",
						}}
					>
						页面出错了
					</h2>
					<p
						style={{
							color: "var(--muted)",
							marginBottom: "24px",
							maxWidth: "480px",
							margin: "0 auto 24px",
						}}
					>
						组件渲染时发生错误，请尝试刷新页面
					</p>
					<button
						onClick={() => this.setState({ hasError: false, error: null })}
						style={{
							padding: "8px 24px",
							borderRadius: "var(--radius-sm)",
							border: "1px solid var(--border)",
							background: "var(--surface)",
							cursor: "pointer",
							fontSize: "0.875rem",
						}}
					>
						重试
					</button>
				</div>
			);
		}

		return this.props.children;
	}
}
