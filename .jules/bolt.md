## 2026-06-11 - Prevent React Renders from High-Frequency Canvas Audio Data
**Learning:** High-frequency data streams (like Web Audio API arrays sent via websockets or internal mics) should never be stored in `useState` if they are only consumed by canvas-based visualizers. This triggers full component tree re-renders up to 60 times a second.
**Action:** Pass `useRef` containing the mutable data array directly to child canvas components. Let the child component read from `ref.current` inside its own `requestAnimationFrame` loop.
