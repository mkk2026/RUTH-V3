# Bolt's Journal
## 2024-06-18 - Avoid storing high-frequency data in React state
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders.
**Action:** Pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own update loops. When implementing continuous rendering loops using `requestAnimationFrame` inside React components (e.g., in `useEffect` for visualizers), always store the animation ID and call `cancelAnimationFrame(animId)` in the cleanup function to prevent severe CPU and memory leaks.

## 2024-06-19 - Zero-allocation audio loop and batched canvas rendering
**Learning:** Frequent object allocation in hot loops like `requestAnimationFrame` (e.g. allocating `new Uint8Array` or calling `Array.from()` every frame) triggers aggressive garbage collection, leading to frame drops and jank. Likewise, executing separate path operations (`beginPath` and `stroke`) in loops inside canvas rendering creates massive CPU overhead due to numerous separate draw calls.
**Action:** Always declare Typed Arrays or object containers *outside* hot loops and assign their data inside. When rendering multiple similar geometric objects on a canvas, wrap the entire collection in a single `beginPath()` and `stroke()` block to batch the draw calls.

## 2024-06-20 - Direct DOM mutation in hot loops instead of React state
**Learning:** Calling React `setState` (even throttled) inside a hot loop like `requestAnimationFrame` causes component re-renders that lead to jank and frame drops.
**Action:** Use `useRef` to store references to the target DOM elements and mutate their `.textContent` or style directly inside the `requestAnimationFrame` loop, bypassing the React render cycle completely. This pattern is particularly useful for rapidly updating telemetry or UI elements.
