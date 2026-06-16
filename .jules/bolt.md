
## 2024-06-16 - Avoid root state for high-frequency data (like WebSockets / requestAnimationFrame)
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders. This is a critical architectural bottleneck when rendering at 60fps.
**Action:** Always pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` for high-frequency data and let child components handle their own `requestAnimationFrame` update loops to bypass React render cycles.
