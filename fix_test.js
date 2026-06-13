const fs = require('fs');
let content = fs.readFileSync('tests/test_cad_agent.py', 'utf8');

// I am NOT touching Python test files because it is NOT related to my changes!
// Wait, the memory states: "The `CadAgent` backend class uses a `router` attribute (instead of `client`) and a `system_instruction` attribute (instead of `system_prompt`) for its language model interactions."
// So I should just fix the tests as per the memory!
content = content.replace(
    /assert hasattr\(agent, 'client'\)/g,
    'assert hasattr(agent, \'router\')'
);

content = content.replace(
    /assert hasattr\(agent, 'system_prompt'\) or hasattr\(agent, 'client'\)/g,
    'assert hasattr(agent, \'system_instruction\') or hasattr(agent, \'router\')'
);

fs.writeFileSync('tests/test_cad_agent.py', content);
