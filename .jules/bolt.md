## 2026-05-12 - Eliminated 60FPS React Re-renders from Audio Visualizer
**Learning:** Frequent updates tied to requestAnimationFrame (like extracting Web Audio analyser data) should never be stored in React state in a top-level component. Doing so triggers cascading re-renders across the entire app tree at 60 FPS, causing severe performance degradation.
**Action:** Always move high-frequency animation loops out of React state and into imperative Canvas/DOM updates within a dedicated component's useEffect, passing stable references (like the analyser node) instead of changing data.
