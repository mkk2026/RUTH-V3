## 2025-03-05 - State management for high-frequency data
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders, crushing performance.
**Action:** Never put high-frequency data in root state. Instead, pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own internal update loops (e.g. via `requestAnimationFrame` drawing directly to a canvas).
