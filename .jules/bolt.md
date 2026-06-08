## 2026-06-08 - [Avoid React State for requestAnimationFrame and Socket Streams]
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders (at 60fps).
**Action:** Always use `useRef` to hold high-frequency continuous data that is passed down to visualizer/canvas child components. The child components should use internal continuous `requestAnimationFrame` loops that read directly from the ref, bypassing React's render cycle completely.
