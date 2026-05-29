## 2024-05-29 - [Avoid App.jsx high-frequency renders]
**Learning:** Avoid storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state, as it causes severe cascading app-wide re-renders. Instead, pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own update loops.
**Action:** Move high frequency data (`aiAudioData`, `micAudioData`) out of `App.jsx` component state.
