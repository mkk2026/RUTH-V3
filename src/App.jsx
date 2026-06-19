import React from 'react';
import NeuralAvatar from './components/NeuralAvatar';

// RUTH-V3 now boots straight into the Neural Avatar as the primary display.
// The avatar owns the Socket.IO connection and starts the RUTH session itself
// (see NeuralAvatar.jsx). The previous multi-window UI is preserved in
// App.legacy.jsx but is no longer rendered.
function App() {
    return (
        <div className="h-screen w-screen bg-black overflow-hidden">
            <NeuralAvatar socketUrl="http://localhost:8000" />
        </div>
    );
}

export default App;
