## 2024-05-18 - Prevent Audio State App Renders
**Learning:** Storing high-frequency array data (like audio analyzer nodes `micAudioData` and Socket.IO `aiAudioData`) in the root `App.jsx` component state causes severe cascading app-wide re-renders 60 times a second.
**Action:** Replace high-frequency array state variables with `useRef`. Pass the refs down to child components, and let those child components handle their own internal `requestAnimationFrame` loops for drawing or calculation.
