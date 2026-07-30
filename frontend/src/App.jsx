import { useState, useEffect } from "react";
import Nav from "./components/Nav";
import HeroSearch from "./components/HeroSearch";
import StatsRow from "./components/StatsRow";
import QueryPanel from "./components/QueryPanel";
import ReversePanel from "./components/ReversePanel";
import HistoryPanel from "./components/HistoryPanel";
import ImportPanel from "./components/ImportPanel";
import ExportPanel from "./components/ExportPanel";
import Footer from "./components/Footer";
import Toast from "./components/Toast";
import API_BASE from "./config";

export default function App() {
	const [activeTab, setActiveTab] = useState("query");
	const [systemStatus, setSystemStatus] = useState("checking");
	const [queryInput, setQueryInput] = useState("");
	const [queryType, setQueryType] = useState("");
	const [toast, setToast] = useState({ message: "", type: "info" });

	useEffect(() => {
		let retryCount = 0;
		const maxRetries = 5;
		const retryDelay = 3000;

		async function checkHealth() {
			try {
				const resp = await fetch(`${API_BASE}/system/health`);
				const data = await resp.json();
				if (data.code === 0 && data.data) {
					setSystemStatus(data.data.status);
					return true;
				}
			} catch {
				// 后端可能未就绪
			}
			return false;
		}

		async function pollHealth() {
			const ok = await checkHealth();
			if (!ok && retryCount < maxRetries) {
				retryCount++;
				setTimeout(pollHealth, retryDelay);
			}
		}

		pollHealth();
	}, []);

	function handleSearch(input, type) {
		setQueryInput(input);
		setQueryType(type);

		if (type === "ip") {
			setActiveTab("reverse");
		} else {
			setActiveTab("query");
		}
	}

	function handleTabChange(tab) {
		setActiveTab(tab);
	}

	function showToast(message, type = "info") {
		setToast({ message, type });
	}

	function handleImportComplete() {
		showToast("数据导入完成", "success");
	}

	return (
		<>
			<Nav
				activeTab={activeTab}
				onTabChange={handleTabChange}
				systemStatus={systemStatus}
			/>

			<HeroSearch onSearch={handleSearch} />

			<section className="tabs-section">
				<div className="container">
					<StatsRow />

					<div className="tab-nav" role="tablist" aria-label="功能标签">
						<button
							className={`tab-btn ${activeTab === "query" ? "active" : ""}`}
							onClick={() => setActiveTab("query")}
							role="tab"
							aria-selected={activeTab === "query"}
							aria-controls="panel-query"
						>
							查询结果
						</button>
						<button
							className={`tab-btn ${activeTab === "reverse" ? "active" : ""}`}
							onClick={() => setActiveTab("reverse")}
							role="tab"
							aria-selected={activeTab === "reverse"}
							aria-controls="panel-reverse"
						>
							IP反查
						</button>
						<button
							className={`tab-btn ${activeTab === "history" ? "active" : ""}`}
							onClick={() => setActiveTab("history")}
							role="tab"
							aria-selected={activeTab === "history"}
							aria-controls="panel-history"
						>
							历史记录
						</button>
						<button
							className={`tab-btn ${activeTab === "import" ? "active" : ""}`}
							onClick={() => setActiveTab("import")}
							role="tab"
							aria-selected={activeTab === "import"}
							aria-controls="panel-import"
						>
							数据导入
						</button>
						<button
							className={`tab-btn ${activeTab === "export" ? "active" : ""}`}
							onClick={() => setActiveTab("export")}
							role="tab"
							aria-selected={activeTab === "export"}
							aria-controls="panel-export"
						>
							数据导出
						</button>
					</div>

					{activeTab === "query" && (
						<QueryPanel queryInput={queryInput} queryType={queryType} />
					)}
					{activeTab === "reverse" && (
						<ReversePanel queryInput={queryInput} queryType={queryType} />
					)}
					{activeTab === "history" && <HistoryPanel />}
					{activeTab === "import" && (
						<ImportPanel onImportComplete={handleImportComplete} />
					)}
					{activeTab === "export" && <ExportPanel />}
				</div>
			</section>

			<Footer />

			<Toast
				message={toast.message}
				type={toast.type}
				onClose={() => setToast({ message: "", type: "info" })}
			/>
		</>
	);
}
