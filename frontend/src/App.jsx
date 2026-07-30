import { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import Nav from "./components/Nav";
import HeroSearch from "./components/HeroSearch";
import StatsRow from "./components/StatsRow";
import QueryPanel from "./components/QueryPanel";
import BatchQueryPanel from "./components/BatchQueryPanel";
import ReversePanel from "./components/ReversePanel";
import HistoryPanel from "./components/HistoryPanel";
import ImportPanel from "./components/ImportPanel";
import ExportPanel from "./components/ExportPanel";
import SettingsPage from "./components/SettingsPage";
import Footer from "./components/Footer";
import Toast from "./components/Toast";
import API_BASE from "./config";

export default function App() {
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
			} catch {}
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
	}

	function showToast(message, type = "info") {
		setToast({ message, type });
	}

	return (
		<>
			<Nav systemStatus={systemStatus} />

			<Routes>
				<Route
					path="/"
					element={
						<>
							<HeroSearch onSearch={handleSearch} />
							<section className="tabs-section">
								<div className="container">
									<StatsRow />
									<QueryPanel queryInput={queryInput} queryType={queryType} />
									{queryInput && (
										<ReversePanel
											queryInput={queryInput}
											queryType={queryType}
										/>
									)}
								</div>
							</section>
						</>
					}
				/>
				<Route
					path="/batch"
					element={
						<section className="tabs-section">
							<div className="container">
								<BatchQueryPanel />
							</div>
						</section>
					}
				/>
				<Route
					path="/history"
					element={
						<section className="tabs-section">
							<div className="container">
								<HistoryPanel />
							</div>
						</section>
					}
				/>
				<Route
					path="/import"
					element={
						<section className="tabs-section">
							<div className="container">
								<ImportPanel
									onImportComplete={() => showToast("数据导入完成", "success")}
								/>
							</div>
						</section>
					}
				/>
				<Route
					path="/export"
					element={
						<section className="tabs-section">
							<div className="container">
								<ExportPanel />
							</div>
						</section>
					}
				/>
				<Route
					path="/settings"
					element={
						<section className="tabs-section">
							<div className="container">
								<SettingsPage />
							</div>
						</section>
					}
				/>
			</Routes>

			<Footer />
			<Toast
				message={toast.message}
				type={toast.type}
				onClose={() => setToast({ message: "", type: "info" })}
			/>
		</>
	);
}
