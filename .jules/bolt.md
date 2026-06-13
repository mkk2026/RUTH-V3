## 2024-05-15 - Frequent React State Updates for Audio Visualizer
**Learning:** Avoid storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (App.jsx) state, as it causes severe cascading app-wide re-renders.
**Action:** Instead, pass the data source (e.g., analyser node, socket) down to child components or use refs and let children handle their own update loops, or pass a mutable ref.
