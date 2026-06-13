const fs = require('fs');

let content = fs.readFileSync('src/App.jsx', 'utf8');

// Replace state with refs
content = content.replace(
    /const \[aiAudioData, setAiAudioData\] = useState\(new Array\(64\)\.fill\(0\)\);/,
    'const aiAudioDataRef = useRef(new Array(64).fill(0));'
);

content = content.replace(
    /const \[micAudioData, setMicAudioData\] = useState\(new Array\(32\)\.fill\(0\)\);/,
    'const micAudioDataRef = useRef(new Array(32).fill(0));'
);

// Update mic data assignment
content = content.replace(
    /setMicAudioData\(Array\.from\(dataArray\)\);/g,
    'micAudioDataRef.current = Array.from(dataArray);'
);

// Update socket event listener
content = content.replace(
    /setAiAudioData\(data\.data\);/g,
    'aiAudioDataRef.current = data.data;'
);

// Remove audioAmp from App.jsx as it will be calculated in Visualizer.jsx
content = content.replace(
    /const audioAmp = aiAudioData\.reduce\(\(a, b\) => a \+ b, 0\) \/ aiAudioData\.length \/ 255;/g,
    ''
);

// Update TopAudioBar prop
content = content.replace(
    /<TopAudioBar audioData=\{micAudioData\} \/>/g,
    '<TopAudioBar audioDataRef={micAudioDataRef} />'
);

// Update Visualizer prop
content = content.replace(
    /audioData=\{aiAudioData\}\n.*intensity=\{audioAmp\}/g,
    'audioDataRef={aiAudioDataRef}'
);

fs.writeFileSync('src/App.jsx', content);
