const fs = require('fs');

let content = fs.readFileSync('src/components/TopAudioBar.jsx', 'utf8');

content = content.replace(
    /const TopAudioBar = \(\{ audioData \}\) => \{/,
    'const TopAudioBar = ({ audioDataRef }) => {'
);

content = content.replace(
    /const value = audioData\[i % audioData\.length\] \|\| 0;/g,
    'const value = audioDataRef.current[i % audioDataRef.current.length] || 0;'
);

content = content.replace(
    /\}, \[audioData\]\);/g,
    '}, [audioDataRef]);'
);

fs.writeFileSync('src/components/TopAudioBar.jsx', content);
