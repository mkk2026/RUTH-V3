## 2024-05-23 - App-Wide Re-renders via Audio Visualization States
**Learning:** Storing high-frequency WebSocket and microphone analyser arrays in `App.jsx` using `useState` triggers severe app-wide cascading re-renders up to 60 times a second. `Visualizer` and `TopAudioBar` components also needlessly triggered React updates.
**Action:** Always use `useRef` to store rapidly updating audio analyzer data and directly pass the refs down to continuous `requestAnimationFrame` loops in child canvas components. Ensure `cancelAnimationFrame` is called on unmount to prevent leaks.
