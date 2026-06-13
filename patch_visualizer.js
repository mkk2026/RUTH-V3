const fs = require('fs');

let content = fs.readFileSync('src/components/Visualizer.jsx', 'utf8');

// Change props to take audioDataRef instead of audioData and intensity
content = content.replace(
    /const Visualizer = \(\{ audioData, isListening, intensity = 0, width = 600, height = 400 \}\) => \{/,
    'const Visualizer = ({ audioDataRef, isListening, width = 600, height = 400 }) => {'
);

// Remove the internal ref copying since we will just use audioDataRef directly
content = content.replace(
    /    const audioDataRef = useRef\(audioData\);\n    const intensityRef = useRef\(intensity\);\n    const isListeningRef = useRef\(isListening\);\n\n    useEffect\(\(\) => \{\n        audioDataRef\.current = audioData;\n        intensityRef\.current = intensity;\n        isListeningRef\.current = isListening;\n    \}, \[audioData, intensity, isListening\]\);\n/,
    '    const isListeningRef = useRef(isListening);\n\n    useEffect(() => {\n        isListeningRef.current = isListening;\n    }, [isListening]);\n'
);

// Update draw function to calculate intensity dynamically
content = content.replace(
    /            const currentIntensity = intensityRef\.current;/,
    '            const currentAudioData = audioDataRef?.current || [];\n            const currentIntensity = currentAudioData.length > 0 \n                ? currentAudioData.reduce((a, b) => a + b, 0) / currentAudioData.length / 255 \n                : 0;'
);

fs.writeFileSync('src/components/Visualizer.jsx', content);
