
## 2024-05-24 - React state triggers 60 FPS main thread blocking for Audio Visualizer
**Learning:** We discovered that storing streaming high-frequency data (like 60 FPS audio buffers) in global `App.jsx` React state (`useState`) triggers massive main-thread blocking, causing a huge number of heavy child components to re-render constantly.
**Action:** Always route high-frequency rendering data through `useRef` and poll the refs locally using `requestAnimationFrame` inside the specific leaf components (e.g. `Visualizer` and `TopAudioBar`) to completely bypass React's render lifecycle for high-frequency updates.
