## 2024-05-24 - Avoiding High-Frequency State Updates in Root Component
**Learning:** Storing high-frequency data (like audio analyzer arrays or frequent socket events) in the root React component (`App.jsx`) state causes severe cascading app-wide re-renders 60 times a second. This is a massive performance bottleneck.
**Action:** Pass the data source (e.g., `analyser` node, `socket` instance) down to child components or use `useRef` and let children handle their own update loops without triggering React state changes.
