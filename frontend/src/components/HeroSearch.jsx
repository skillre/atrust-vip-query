import { useState } from "react";

export default function HeroSearch({ onSearch }) {
	const [input, setInput] = useState("");
	const [type, setType] = useState("user");
	// 自动识别：输入 11 位纯数字视为手机号查询
	const isPhoneInput = /^\d{11}$/.test(input.trim());

	const handleKeyDown = (e) => {
		if (e.key === "Enter") {
			handleSearch();
		}
	};

	const handleSearch = () => {
		if (input.trim()) {
			onSearch(input.trim(), type);
		}
	};

	return (
		<section className="hero">
			<div className="container">
				<h1 className="hero-title">虚拟IP查询</h1>
				<p className="hero-subtitle">
					快速查询 aTrust
					零信任系统分配给用户的虚拟IP地址，支持用户名、手机号查询和IP反查
				</p>
				<div className="search-box">
					<svg
						className="search-icon"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						strokeWidth="2"
					>
						<circle cx="11" cy="11" r="8" />
						<path d="M21 21l-4.35-4.35" />
					</svg>
					<input
						type="text"
						placeholder="输入用户名、显示名、手机号或虚拟IP地址..."
						autoComplete="off"
						aria-label="搜索用户名、手机号或IP地址"
						value={input}
						onChange={(e) => setInput(e.target.value)}
						onKeyDown={handleKeyDown}
					/>
					<div className="search-type-select">
						<select
							value={type}
							onChange={(e) => setType(e.target.value)}
							aria-label="搜索类型"
						>
							<option value="user">按用户查询</option>
							<option value="ip">按IP反查</option>
						</select>
					</div>
					<button
						className="search-btn"
						onClick={handleSearch}
						aria-label="执行查询"
					>
						查询
					</button>
				</div>
				<div className="search-hints">
					<span>支持模糊搜索</span>
					<span>按 Enter 快速查询</span>
					{isPhoneInput && <span className="search-hint-phone">检测到手机号，将按手机号精确查询</span>}
				</div>
			</div>
		</section>
	);
}
