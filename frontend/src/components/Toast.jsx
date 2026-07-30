import { useState, useEffect } from "react";

export default function Toast({ message, type, onClose }) {
	const [visible, setVisible] = useState(false);

	useEffect(() => {
		if (message) {
			setVisible(true);
			const timer = setTimeout(() => {
				setVisible(false);
				if (onClose) onClose();
			}, 3000);
			return () => clearTimeout(timer);
		}
	}, [message, onClose]);

	if (!message) return null;

	return (
		<div className={`toast ${type || "info"}`} role="alert" aria-live="polite">
			{message}
		</div>
	);
}
