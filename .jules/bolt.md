## 2024-05-21 - Avoid high-frequency state updates in root component
**Learning:** Storing high-frequency data (like audio analyzer arrays from `requestAnimationFrame` or frequent socket events) in `App.jsx` state causes severe cascading app-wide re-renders, killing performance.
**Action:** Use `useRef` to store high-frequency data and let child components (like `Visualizer` or `TopAudioBar`) run their own `requestAnimationFrame` update loops, reading from the refs or data sources directly without triggering React state updates.
