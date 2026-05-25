## 2024-05-25 - Avoid root state for high-frequency data
**Learning:** High frequency audio data (mic and socket) stored in root component state triggers continuous cascading re-renders. Refactoring child components to handle socket events and animation loops locally bypassing React state yields massive performance gains.
**Action:** Always move high-frequency socket listeners or requestAnimationFrame polling directly into the child component (using refs and local canvases) instead of lifting the state up.
