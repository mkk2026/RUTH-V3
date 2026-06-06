## 2026-06-06 - [React State Performance Bottleneck]
**Learning:** Frequent React state updates for continuous high-frequency data (like reading Web Audio API Analyser output 60 FPS) in root components trigger complete component tree re-renders and cause severe performance degradation.
**Action:** Avoid tracking rapidly updating visual data in React state. Pass refs to data sources directly to child visualizer components, and let the child component draw directly to canvas using an internal `requestAnimationFrame` loop to sidestep the React render cycle completely.
