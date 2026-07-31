import { useEffect } from "react";

/**
 * 导入进度弹窗 —— 还原设计稿「Import Progress Modal Screen」。
 *
 * 后端 /import/upload 是一次性同步请求，无法上报真实百分比，
 * 因此这里用「阶段驱动 + 平滑推进」模拟进度：
 *   parsing(文件解析) → validating(数据验证) → importing(导入数据库) → done / error(完成/失败)
 * 请求真正返回后由父组件把 phase 置为 done，并带上真实 result。
 *
 * Props:
 *   file      : 正在导入的 File 对象（用于展示文件名/大小）
 *   phase     : 当前阶段 parsing | validating | importing | done | error
 *   percent   : 0-100 进度百分比
 *   result    : 导入结果 { imported, total_rows, message, ... }（done/error 时有值）
 *   errorMsg  : 失败信息（phase=error 时展示）
 *   onClose   : 关闭回调
 */

const STEPS = [
	{ key: "parsing", label: "文件解析" },
	{ key: "validating", label: "数据验证" },
	{ key: "importing", label: "导入数据库" },
	{ key: "done", label: "完成" },
];

// 阶段推进顺序，用于判断某一步是「已完成 / 进行中 / 待办」
const PHASE_ORDER = ["parsing", "validating", "importing", "done"];

function formatFileSize(bytes) {
	if (!bytes) return "-";
	if (bytes < 1024) return bytes + " B";
	if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
	return (bytes / 1048576).toFixed(1) + " MB";
}

function CheckIcon() {
	return (
		<svg
			width="12"
			height="12"
			viewBox="0 0 24 24"
			fill="none"
			stroke="#fff"
			strokeWidth="3"
		>
			<path d="M5 13l4 4 10-10" />
		</svg>
	);
}

function SpinnerIcon() {
	return (
		<svg
			className="ipm-spin"
			width="12"
			height="12"
			viewBox="0 0 24 24"
			fill="none"
			stroke="#fff"
			strokeWidth="2.5"
		>
			<path d="M4 4v5h.582m15.356 2a8.001 8.001 0 0 0-15.356-2m0 0h4.418M20 20v-5h-.581m0 0a8.003 8.003 0 0 1-15.357-2m15.357 2h-4.419" />
		</svg>
	);
}

function ClockIcon() {
	return (
		<svg
			width="12"
			height="12"
			viewBox="0 0 24 24"
			fill="none"
			stroke="var(--text-muted)"
			strokeWidth="2"
		>
			<circle cx="12" cy="12" r="9" />
			<path d="M12 8v4l3 3" />
		</svg>
	);
}

export default function ImportProgressModal({
	file,
	phase = "parsing",
	percent = 0,
	result = null,
	errorMsg = "",
	onClose,
}) {
	// 完成 / 失败前禁止 ESC 关闭，避免误触中断（这里仅允许显式关闭）
	useEffect(() => {
		function onKey(e) {
			if (e.key === "Escape" && (phase === "done" || phase === "error")) {
				onClose?.();
			}
		}
		window.addEventListener("keydown", onKey);
		return () => window.removeEventListener("keydown", onKey);
	}, [phase, onClose]);

	const isError = phase === "error";
	const isDone = phase === "done";
	const closable = isDone || isError;

	const currentIdx = PHASE_ORDER.indexOf(
		phase === "error" ? "importing" : phase,
	);
	const displayPercent = Math.min(100, Math.max(0, Math.round(percent)));

	const total = result?.total_rows ?? result?.total ?? 0;
	const imported = result?.imported ?? result?.success ?? 0;
	const estRecords =
		total || (file ? Math.max(1, Math.round(file.size / 190)) : 0);
	const processed = isDone
		? imported
		: Math.round((estRecords * displayPercent) / 100);

	const title = isError ? "导入失败" : isDone ? "导入完成" : "正在导入数据";

	function stepState(stepKey) {
		if (isError) {
			// 失败：已过的步骤为完成，导入数据库步骤标记为失败态
			const idx = PHASE_ORDER.indexOf(stepKey);
			if (idx < currentIdx) return "done";
			if (idx === currentIdx) return "error";
			return "pending";
		}
		const idx = PHASE_ORDER.indexOf(stepKey);
		if (idx < currentIdx) return "done";
		if (idx === currentIdx) return isDone ? "done" : "active";
		return "pending";
	}

	return (
		<div
			className="modal-overlay ipm-overlay"
			onClick={() => closable && onClose?.()}
		>
			<div className="ipm-modal" onClick={(e) => e.stopPropagation()}>
				{/* Header */}
				<div className="ipm-header">
					<span className="ipm-title">{title}</span>
					<button
						className="modal-close"
						onClick={() => onClose?.()}
						disabled={!closable}
						title={closable ? "关闭" : "导入进行中…"}
						style={{
							opacity: closable ? 1 : 0.4,
							cursor: closable ? "pointer" : "not-allowed",
						}}
					>
						<svg
							width="14"
							height="14"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							strokeWidth="2"
						>
							<path d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>

				{/* Body */}
				<div className="ipm-body">
					{/* File Info */}
					<div className="ipm-file">
						<div className="ipm-file-icon">
							<svg
								width="22"
								height="22"
								viewBox="0 0 24 24"
								fill="none"
								stroke="var(--accent)"
								strokeWidth="2"
							>
								<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
								<polyline points="14 2 14 8 20 8" />
								<line x1="9" y1="13" x2="15" y2="13" />
								<line x1="9" y1="17" x2="15" y2="17" />
							</svg>
						</div>
						<div className="ipm-file-detail">
							<div className="ipm-file-name">{file?.name || "-"}</div>
							<div className="ipm-file-sub">
								{formatFileSize(file?.size)}
								{estRecords
									? ` · 预计 ${estRecords.toLocaleString()} 条记录`
									: ""}
							</div>
						</div>
					</div>

					{/* Progress */}
					<div className="ipm-progress">
						<div className="progress-bar">
							<div
								className={`progress-fill${isError ? " ipm-fill-error" : ""}`}
								style={{ width: `${displayPercent}%` }}
							/>
						</div>
						<div className="ipm-progress-info">
							<span
								className={`ipm-percent${isError ? " ipm-percent-error" : ""}`}
							>
								{isError ? "已中断" : `${displayPercent}%`}
							</span>
							<span className="ipm-processed">
								{isDone
									? `${imported.toLocaleString()} / ${total.toLocaleString()} 条已导入`
									: `${processed.toLocaleString()} / ${estRecords.toLocaleString()} 条已处理`}
							</span>
						</div>
					</div>

					{/* Steps */}
					<div className="ipm-steps">
						{STEPS.map((s) => {
							const st = stepState(s.key);
							return (
								<div key={s.key} className={`ipm-step ipm-step-${st}`}>
									<span className={`ipm-step-icon ipm-icon-${st}`}>
										{st === "done" && <CheckIcon />}
										{st === "active" && <SpinnerIcon />}
										{st === "error" && (
											<svg
												width="12"
												height="12"
												viewBox="0 0 24 24"
												fill="none"
												stroke="#fff"
												strokeWidth="3"
											>
												<path d="M6 18L18 6M6 6l12 12" />
											</svg>
										)}
										{st === "pending" && <ClockIcon />}
									</span>
									<span className="ipm-step-label">{s.label}</span>
								</div>
							);
						})}
					</div>

					{/* Footer text */}
					<div className="ipm-foot-text">
						{isError
							? errorMsg || result?.message || "导入过程中发生错误"
							: isDone
								? result?.message || "数据已成功导入"
								: "预计剩余时间: 数秒"}
					</div>
				</div>
			</div>
		</div>
	);
}
