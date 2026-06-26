# Bolt's Journal
## 2024-06-18 - Avoid storing high-frequency data in React state
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders.
**Action:** Pass the data source (e.g., `analyser` node, `socket`) down to child components or use `useRef` and let children handle their own update loops. When implementing continuous rendering loops using `requestAnimationFrame` inside React components (e.g., in `useEffect` for visualizers), always store the animation ID and call `cancelAnimationFrame(animId)` in the cleanup function to prevent severe CPU and memory leaks.

## 2024-06-19 - Zero-allocation audio loop and batched canvas rendering
**Learning:** Frequent object allocation in hot loops like `requestAnimationFrame` (e.g. allocating `new Uint8Array` or calling `Array.from()` every frame) triggers aggressive garbage collection, leading to frame drops and jank. Likewise, executing separate path operations (`beginPath` and `stroke`) in loops inside canvas rendering creates massive CPU overhead due to numerous separate draw calls.
**Action:** Always declare Typed Arrays or object containers *outside* hot loops and assign their data inside. When rendering multiple similar geometric objects on a canvas, wrap the entire collection in a single `beginPath()` and `stroke()` block to batch the draw calls.

## 2024-06-26 - Avoid higher-order array functions in hot loops
**Learning:** Using higher-order array functions like `Array.prototype.reduce`, `map`, or `forEach` inside high-frequency `requestAnimationFrame` loops (like audio visualizers) on large typed arrays creates significant per-element callback allocation overhead. This overhead adds up quickly when analyzing hundreds of audio frequency bins per frame, causing measurable CPU strain and potential frame drops.
**Action:** Avoid using `reduce` or similar higher-order functions inside hot rendering loops. Use a standard `for` loop instead, which eliminates the callback allocation overhead and runs significantly faster in this context.
