const fs = require('fs');

let content = fs.readFileSync('src/components/TopAudioBar.jsx', 'utf8');

// I need to make sure the animation loops and gets cancelled
content = content.replace(
    /requestAnimationFrame\(draw\);/g,
    'let animationId;\n        const loop = () => {\n            draw();\n            animationId = requestAnimationFrame(loop);\n        };\n        loop();\n        return () => cancelAnimationFrame(animationId);'
);

fs.writeFileSync('src/components/TopAudioBar.jsx', content);
