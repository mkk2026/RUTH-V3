## 2026-05-14 - React Ref Optimizaton For High-Frequency Streams
**Learning:** The application was updating React state 60 times a second using high frequency tracking logic loops inside `App.jsx` causing massive unnecessary re-renders across the whole component tree.
**Action:** Next time an issue requires tracking high frequency streaming data (such as position or sound streams that drive canvas operations), prefer to pass a `useRef` and let the receiving component poll it inside its own `requestAnimationFrame` instead of relying on React state and VDOM patching.
