## 2024-05-18 - High-Frequency State Updates Cause App-wide Re-Renders
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders and degrades overall performance.
**Action:** Always pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own update loops using `requestAnimationFrame` for visualization or UI updates. Make sure to clean up the animation frame on unmount.
