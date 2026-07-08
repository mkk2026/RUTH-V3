# Bolt's Journal
## 2024-06-18 - Avoid storing high-frequency data in React state
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders.
**Action:** Pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own update loops. When implementing continuous rendering loops using `requestAnimationFrame` inside React components (e.g., in `useEffect` for visualizers), always store the animation ID and call `cancelAnimationFrame(animId)` in the cleanup function to prevent severe CPU and memory leaks.

## 2024-06-19 - Zero-allocation audio loop and batched canvas rendering
**Learning:** Frequent object allocation in hot loops like `requestAnimationFrame` (e.g. allocating `new Uint8Array` or calling `Array.from()` every frame) triggers aggressive garbage collection, leading to frame drops and jank. Likewise, executing separate path operations (`beginPath` and `stroke`) in loops inside canvas rendering creates massive CPU overhead due to numerous separate draw calls.
**Action:** Always declare Typed Arrays or object containers *outside* hot loops and assign their data inside. When rendering multiple similar geometric objects on a canvas, wrap the entire collection in a single `beginPath()` and `stroke()` block to batch the draw calls.

## 2024-07-08 - Avoid React setState in requestAnimationFrame and fix floating point modulo logic
**Learning:** Calling React `setState` inside `requestAnimationFrame` loops (even when throttled) causes severe main thread blocking due to constant React render cycles. Furthermore, using time-based floating point modulo arithmetic for throttling (e.g., `Math.floor(time * 10) % 5 === 0`) can evaluate to `true` for multiple consecutive frames depending on the delta time, leading to unexpected burst executions.
**Action:** Use `useRef` to store references to DOM elements and mutate them directly via `ref.current.textContent` for rapidly updating UI telemetry. Always use an integer frame counter (e.g., `frameCount % 6 === 0`) for throttling logic inside animation loops to guarantee single-frame execution.
