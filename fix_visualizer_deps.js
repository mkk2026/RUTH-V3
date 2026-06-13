const fs = require('fs');

let content = fs.readFileSync('src/components/Visualizer.jsx', 'utf8');

content = content.replace(
    /    \}, \[width, height\]\);/g,
    '    }, [width, height, audioDataRef]);'
);

fs.writeFileSync('src/components/Visualizer.jsx', content);
