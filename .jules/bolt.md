# Bolt's Journal
## 2024-06-18 - Avoid storing high-frequency data in React state
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders.
**Action:** Pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own update loops. When implementing continuous rendering loops using `requestAnimationFrame` inside React components (e.g., in `useEffect` for visualizers), always store the animation ID and call `cancelAnimationFrame(animId)` in the cleanup function to prevent severe CPU and memory leaks.

## 2024-06-19 - Zero-allocation audio loop and batched canvas rendering
**Learning:** Frequent object allocation in hot loops like `requestAnimationFrame` (e.g. allocating `new Uint8Array` or calling `Array.from()` every frame) triggers aggressive garbage collection, leading to frame drops and jank. Likewise, executing separate path operations (`beginPath` and `stroke`) in loops inside canvas rendering creates massive CPU overhead due to numerous separate draw calls.
**Action:** Always declare Typed Arrays or object containers *outside* hot loops and assign their data inside. When rendering multiple similar geometric objects on a canvas, wrap the entire collection in a single `beginPath()` and `stroke()` block to batch the draw calls.

## 2024-07-06 - Avoid React state thrashing in requestAnimationFrame loops
**Learning:** Calling React `setState` inside `requestAnimationFrame` loops, even when throttled with time-based logic, causes severe state thrashing across frames. Also, time-based floating-point modulo arithmetic (e.g. `Math.floor(time * 10) % 5 === 0`) can evaluate to true for multiple consecutive frames, resulting in burst executions.
**Action:** Use `useRef` for direct DOM mutations (e.g., `ref.current.textContent`) to update telemetry or UI elements inside `requestAnimationFrame` to avoid React re-renders. Use an integer frame counter (e.g., `frameCount % 6 === 0`) to guarantee single-frame execution for throttling inside `rAF`.
