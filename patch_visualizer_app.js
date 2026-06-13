const fs = require('fs');

let content = fs.readFileSync('src/App.jsx', 'utf8');

content = content.replace(
    /audioData=\{aiAudioData\}\n.*isListening=\{isConnected && !isMuted\}\n.*intensity=\{audioAmp\}/g,
    'audioDataRef={aiAudioDataRef}\n                            isListening={isConnected && !isMuted}'
);

fs.writeFileSync('src/App.jsx', content);
