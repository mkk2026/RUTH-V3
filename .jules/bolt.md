# Bolt's Journal
## 2024-06-18 - Avoid storing high-frequency data in React state
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders.
**Action:** Pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own update loops. When implementing continuous rendering loops using `requestAnimationFrame` inside React components (e.g., in `useEffect` for visualizers), always store the animation ID and call `cancelAnimationFrame(animId)` in the cleanup function to prevent severe CPU and memory leaks.

## 2024-06-19 - Zero-allocation audio loop and batched canvas rendering
**Learning:** Frequent object allocation in hot loops like `requestAnimationFrame` (e.g. allocating `new Uint8Array` or calling `Array.from()` every frame) triggers aggressive garbage collection, leading to frame drops and jank. Likewise, executing separate path operations (`beginPath` and `stroke`) in loops inside canvas rendering creates massive CPU overhead due to numerous separate draw calls.
**Action:** Always declare Typed Arrays or object containers *outside* hot loops and assign their data inside. When rendering multiple similar geometric objects on a canvas, wrap the entire collection in a single `beginPath()` and `stroke()` block to batch the draw calls.
## 2026-07-01 - [Integer frame counting for throttled loops]
**Learning:** [Time-based throttling using Math.floor(time * x) % y in requestAnimationFrame loops can inadvertently trigger state updates multiple times in a row due to floating point and execution timing. Furthermore, hardcoded values in JSX when bypassing React with refs can cause flicker on subsequent natural React renders]
**Action:** [Use an integer frame count variable inside the closure and increment it per frame instead of relying on time. Also leave hardcoded JSX values empty when they will be populated by refs.]
