# Bolt's Journal
## 2024-06-18 - Avoid storing high-frequency data in React state
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders.
**Action:** Pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own update loops. When implementing continuous rendering loops using `requestAnimationFrame` inside React components (e.g., in `useEffect` for visualizers), always store the animation ID and call `cancelAnimationFrame(animId)` in the cleanup function to prevent severe CPU and memory leaks.
