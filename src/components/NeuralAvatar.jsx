import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { io } from 'socket.io-client';
import './NeuralAvatar.css';

// ==========================================
// STATE MACHINE
// ==========================================
const STATE = {
  IDLE: 'idle',
  LISTENING: 'listening',
  THINKING: 'thinking',
  TOOL_CALL: 'tool_call',
  SPEAKING: 'speaking'
};

// ==========================================
// TOOL REGISTRY (matches RUTH-V3 tools)
// ==========================================
const TOOL_REGISTRY = {
  system_info: { name: 'System Info', icon: '💻', color: '#00d4ff' },
  execute_command: { name: 'Terminal', icon: '⚡', color: '#ff00ff' },
  write_file: { name: 'File Writer', icon: '📝', color: '#ffa500' },
  read_file: { name: 'File Reader', icon: '📄', color: '#00ff88' },
  run_code: { name: 'Code Runner', icon: '🔢', color: '#ff00ff' },
  generate_cad: { name: 'CAD Generator', icon: '🎨', color: '#ffa500' },
  slice_and_print: { name: '3D Printer', icon: '🖨️', color: '#00d4ff' },
  web_agent: { name: 'Web Agent', icon: '🌐', color: '#00ff88' },
  search_shodan: { name: 'Shodan', icon: '🔍', color: '#ff0000' },
  nmap_scan: { name: 'Nmap', icon: '🛡️', color: '#ff0000' },
  port_scan: { name: 'Port Scan', icon: '🔌', color: '#ffa500' },
  kasa_control: { name: 'Smart Home', icon: '🏠', color: '#00d4ff' },
  send_telegram: { name: 'Telegram', icon: '✈️', color: '#00d4ff' },
  send_discord: { name: 'Discord', icon: '💬', color: '#5865F2' },
  schedule_task: { name: 'Scheduler', icon: '⏰', color: '#ffa500' },
  monitor_heartbeat: { name: 'Monitor', icon: '💓', color: '#ff0000' },
  mcp_tool: { name: 'MCP Tool', icon: '🔧', color: '#00ff88' },
  memory_recall: { name: 'Memory', icon: '🧠', color: '#00d4ff' },
  memory_store: { name: 'Memory Store', icon: '💾', color: '#00d4ff' },
  study_document: { name: 'Document Study', icon: '📚', color: '#ffa500' },
  create_project: { name: 'Project', icon: '📁', color: '#00ff88' },
  switch_project: { name: 'Switch Project', icon: '🔄', color: '#00d4ff' },
  authenticate: { name: 'Face Auth', icon: '👤', color: '#00ff88' },
  gesture_control: { name: 'Gesture', icon: '👋', color: '#ff00ff' },
  sandbox_execute: { name: 'Sandbox', icon: '🧪', color: '#ffa500' }
};

// ==========================================
// MAIN COMPONENT
// ==========================================
export default function NeuralAvatar({ socketUrl = 'http://localhost:8000', bootSession = true }) {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const socketRef = useRef(null);
  const [currentState, setCurrentState] = useState(STATE.IDLE);
  const [thoughtText, setThoughtText] = useState('');
  const [toolNotification, setToolNotification] = useState(null);
  const loadMetricRef = useRef(null);
  const velocityMetricRef = useRef(null);
  const nodesMetricRef = useRef(null);
  const fluxMetricRef = useRef(null);
  const [activeTools, setActiveTools] = useState(new Set());
  const [isConnected, setIsConnected] = useState(false);
  const [userInput, setUserInput] = useState('');
  const [isMicActive, setIsMicActive] = useState(false);

  const timeRef = useRef(0);
  const neuralActivityRef = useRef(0);
  const activeNodeCountRef = useRef(0);
  const tokenVelocityRef = useRef(0);
  const mouseRef = useRef({ x: 0, y: 0 });
  const recognitionRef = useRef(null);
  const stateRef = useRef(STATE.IDLE);
  const jawGroupRef = useRef(null);
  const brainLightRef = useRef(null);
  const headMaterialRef = useRef(null);
  const particlesMatRef = useRef(null);
  const nodesRef = useRef([]);
  const connectionsRef = useRef([]);
  const brainNodesRef = useRef([]);
  const brainLinesRef = useRef([]);
  const packetGeoRef = useRef(null);
  const packetMatRef = useRef(null);
  const neuralNetworkRef = useRef(null);
  const headGroupRef = useRef(null);
  const leftPupilRef = useRef(null);
  const rightPupilRef = useRef(null);
  const wireMeshRef = useRef(null);
  const particlesGeoRef = useRef(null);
  const particleVelocitiesRef = useRef([]);
  const particlePhasesRef = useRef([]);
  const rendererRef = useRef(null);
  const composerRef = useRef(null);
  const cameraRef = useRef(null);
  const sceneObjRef = useRef(null);
  const animFrameRef = useRef(null);
  const typingIntervalRef = useRef(null);
  const toolTimeoutRef = useRef(null);
  // Fallback idle timer: RUTH-V3 streams transcription deltas with no explicit
  // "turn complete" event, so we return to IDLE after a quiet gap.
  const idleTimerRef = useRef(null);

  // Keep stateRef in sync
  useEffect(() => { stateRef.current = currentState; }, [currentState]);

  // ==========================================
  // SOCKET.IO CONNECTION
  // ==========================================
  useEffect(() => {
    const socket = io(socketUrl, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 10
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('[NeuralAvatar] Connected to RUTH-V3');
      setIsConnected(true);
      socket.emit('avatar_register', { type: 'neural_avatar' });
      // As the primary RUTH display, boot the backend voice/session loop so that
      // text and voice 'user_input' is accepted. Start muted: the avatar drives
      // voice via the browser mic button, so the backend mic stays paused.
      if (bootSession) {
        socket.emit('start_audio', { muted: true });
        socket.emit('discover_kasa');
        socket.emit('discover_printers');
      }
    });

    socket.on('disconnect', () => {
      console.log('[NeuralAvatar] Disconnected from RUTH-V3');
      setIsConnected(false);
    });

    // RUTH-V3 Event Handlers
    socket.on('ruth_listening', () => {
      setCurrentState(STATE.LISTENING);
      setThoughtText('Listening...');
    });

    socket.on('ruth_thinking', (data) => {
      setCurrentState(STATE.THINKING);
      if (data?.thought) {
        typeThought(data.thought);
      }
      neuralActivityRef.current = 0.7;
      activateRandomNodes(20);
    });

    socket.on('ruth_tool_call', (data) => {
      setCurrentState(STATE.TOOL_CALL);
      const toolKey = data?.tool_name || 'system_info';
      const tool = TOOL_REGISTRY[toolKey] || { name: toolKey, icon: '🔧', color: '#ffa500' };

      setToolNotification({
        name: tool.name,
        desc: data?.description || `Executing ${tool.name}...`,
        icon: tool.icon,
        color: tool.color
      });

      setActiveTools(prev => new Set(prev).add(toolKey));
      neuralActivityRef.current = 0.95;
      activateRandomNodes(40);

      if (toolTimeoutRef.current) clearTimeout(toolTimeoutRef.current);
      toolTimeoutRef.current = setTimeout(() => {
        setToolNotification(null);
        setActiveTools(prev => {
          const next = new Set(prev);
          next.delete(toolKey);
          return next;
        });
      }, 3000);
    });

    socket.on('ruth_speaking', () => {
      setCurrentState(STATE.SPEAKING);
    });

    socket.on('ruth_token', (data) => {
      if (data?.token) {
        setThoughtText(prev => prev + data.token);
        tokenVelocityRef.current = 25;
        // Jaw movement
        if (jawGroupRef.current && data.token !== ' ') {
          jawGroupRef.current.rotation.x = Math.sin(Date.now() * 0.01) * 0.15;
        }
        // Neural sync
        if (Math.random() > 0.7) {
          spawnRandomPackets(1, 0xffffff);
          if (brainLightRef.current) {
            brainLightRef.current.intensity = 0.5 + Math.random() * 1.5;
          }
        }
      }
    });

    socket.on('ruth_response_complete', () => {
      setCurrentState(STATE.IDLE);
      setThoughtText('');
      tokenVelocityRef.current = 0;
      if (jawGroupRef.current) jawGroupRef.current.rotation.x = 0;
      if (brainLightRef.current) brainLightRef.current.intensity = 0;
    });

    socket.on('ruth_transcription', (data) => {
      if (data?.text) {
        setUserInput(data.text);
      }
    });

    socket.on('ruth_error', (data) => {
      setThoughtText(`Error: ${data?.message || 'Unknown error'}`);
      setCurrentState(STATE.IDLE);
    });

    // Fallback: generic state events
    socket.on('state_change', (data) => {
      if (data?.state && Object.values(STATE).includes(data.state)) {
        setCurrentState(data.state);
      }
    });

    // ----------------------------------------------------------------------
    // COMPATIBILITY: drive the avatar from RUTH-V3's existing event protocol
    // so it animates even without the optional ruth_* backend emits.
    // ----------------------------------------------------------------------
    const armIdle = () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      idleTimerRef.current = setTimeout(() => {
        setCurrentState(STATE.IDLE);
        setThoughtText('');
        tokenVelocityRef.current = 0;
        if (jawGroupRef.current) jawGroupRef.current.rotation.x = 0;
        if (brainLightRef.current) brainLightRef.current.intensity = 0;
      }, 1500);
    };

    // backend/server.py on_transcription -> {sender: "User"|"RUTH", text}
    socket.on('transcription', (data) => {
      if (!data?.text) return;
      if (data.sender === 'RUTH') {
        if (stateRef.current !== STATE.SPEAKING) setThoughtText('');
        setCurrentState(STATE.SPEAKING);
        setThoughtText(prev => prev + data.text);
        tokenVelocityRef.current = 25;
        if (jawGroupRef.current && data.text.trim()) {
          jawGroupRef.current.rotation.x = Math.sin(Date.now() * 0.01) * 0.15;
        }
        if (Math.random() > 0.7) {
          spawnRandomPackets(1, 0xffffff);
          if (brainLightRef.current) brainLightRef.current.intensity = 0.5 + Math.random() * 1.5;
        }
        armIdle();
      } else {
        // User STT delta arriving -> RUTH is listening
        setCurrentState(STATE.LISTENING);
        armIdle();
      }
    });

    // backend/server.py on_tool_confirmation -> {id, tool, args}
    socket.on('tool_confirmation_request', (data) => {
      const toolKey = data?.tool || 'system_info';
      const tool = TOOL_REGISTRY[toolKey] || { name: toolKey, icon: '🔧', color: '#ffa500' };
      setCurrentState(STATE.TOOL_CALL);
      setToolNotification({
        name: tool.name,
        desc: `Awaiting confirmation: ${tool.name}`,
        icon: tool.icon,
        color: tool.color
      });
      setActiveTools(prev => new Set(prev).add(toolKey));
      neuralActivityRef.current = 0.95;
      activateRandomNodes(40);
      if (toolTimeoutRef.current) clearTimeout(toolTimeoutRef.current);
      toolTimeoutRef.current = setTimeout(() => {
        setToolNotification(null);
        setActiveTools(prev => { const n = new Set(prev); n.delete(toolKey); return n; });
      }, 4000);
    });

    // backend/server.py on_error -> {msg}
    socket.on('error', (data) => {
      if (data?.msg) {
        setThoughtText(`Error: ${data.msg}`);
        armIdle();
      }
    });

    return () => {
      socket.disconnect();
      if (toolTimeoutRef.current) clearTimeout(toolTimeoutRef.current);
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    };
  }, [socketUrl]);

  // ==========================================
  // THREE.JS SCENE SETUP
  // ==========================================
  useEffect(() => {
    if (!containerRef.current) return;

    // Scene
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x000000, 0.02);
    sceneObjRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(45, containerRef.current.clientWidth / containerRef.current.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 12);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ReinhardToneMapping;
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Post-processing
    const composer = new EffectComposer(renderer);
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(containerRef.current.clientWidth, containerRef.current.clientHeight),
      1.5, 0.4, 0.85
    );
    bloomPass.threshold = 0.2;
    bloomPass.strength = 1.2;
    bloomPass.radius = 0.5;
    composer.addPass(bloomPass);
    const outputPass = new OutputPass();
    composer.addPass(outputPass);
    composerRef.current = composer;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x001133, 0.5);
    scene.add(ambientLight);
    const keyLight = new THREE.DirectionalLight(0x00d4ff, 2);
    keyLight.position.set(5, 5, 5);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xff00aa, 0.5);
    fillLight.position.set(-5, 0, 5);
    scene.add(fillLight);
    const rimLight = new THREE.DirectionalLight(0x00d4ff, 1.5);
    rimLight.position.set(0, 5, -5);
    scene.add(rimLight);
    const brainLight = new THREE.PointLight(0x00d4ff, 0, 10);
    brainLight.position.set(0, 0, 0);
    scene.add(brainLight);
    brainLightRef.current = brainLight;

    // ==========================================
    // AVATAR HEAD
    // ==========================================
    const headGroup = new THREE.Group();
    scene.add(headGroup);
    headGroupRef.current = headGroup;

    // Head geometry
    const headGeo = new THREE.IcosahedronGeometry(1.8, 32);
    const posAttribute = headGeo.attributes.position;
    const vertex = new THREE.Vector3();
    for (let i = 0; i < posAttribute.count; i++) {
      vertex.fromBufferAttribute(posAttribute, i);
      const len = vertex.length();
      const n = vertex.clone().normalize();
      if (n.z > 0.3) { vertex.z *= 0.85; vertex.x *= 1.05; }
      if (n.y < -0.3 && n.z > 0.2) { vertex.y -= 0.2; vertex.z += 0.1; }
      if (n.y > 0.5 && n.z > 0) { vertex.z *= 1.1; }
      const noise = Math.sin(vertex.x * 3) * Math.cos(vertex.y * 3) * 0.02;
      vertex.addScaledVector(n, noise);
      posAttribute.setXYZ(i, vertex.x, vertex.y, vertex.z);
    }
    headGeo.computeVertexNormals();

    const headMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x0a0a1a, metalness: 0.9, roughness: 0.2,
      clearcoat: 1.0, clearcoatRoughness: 0.1,
      transmission: 0.1, thickness: 0.5,
      emissive: 0x001133, emissiveIntensity: 0.2,
      transparent: true, opacity: 0.95
    });
    headMaterialRef.current = headMaterial;
    const headMesh = new THREE.Mesh(headGeo, headMaterial);
    headGroup.add(headMesh);

    // Wireframe
    const wireGeo = new THREE.IcosahedronGeometry(1.82, 16);
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x00d4ff, wireframe: true, transparent: true, opacity: 0.05
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    headGroup.add(wireMesh);
    wireMeshRef.current = wireMesh;

    // Eyes
    const eyeGeo = new THREE.SphereGeometry(0.25, 32, 32);
    const eyeMat = new THREE.MeshPhysicalMaterial({
      color: 0x000000, emissive: 0x00d4ff, emissiveIntensity: 2,
      metalness: 1, roughness: 0
    });
    const leftEye = new THREE.Mesh(eyeGeo, eyeMat.clone());
    leftEye.position.set(-0.6, 0.2, 1.45);
    headGroup.add(leftEye);
    const rightEye = new THREE.Mesh(eyeGeo, eyeMat.clone());
    rightEye.position.set(0.6, 0.2, 1.45);
    headGroup.add(rightEye);

    const pupilGeo = new THREE.SphereGeometry(0.1, 16, 16);
    const pupilMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const leftPupil = new THREE.Mesh(pupilGeo, pupilMat);
    leftPupil.position.set(0, 0, 0.22);
    leftEye.add(leftPupil);
    leftPupilRef.current = leftPupil;
    const rightPupil = new THREE.Mesh(pupilGeo, pupilMat);
    rightPupil.position.set(0, 0, 0.22);
    rightEye.add(rightPupil);
    rightPupilRef.current = rightPupil;

    // Jaw
    const jawGroup = new THREE.Group();
    const jawGeo = new THREE.BoxGeometry(1.2, 0.4, 0.8);
    const jawMat = new THREE.MeshPhysicalMaterial({
      color: 0x0a0a1a, metalness: 0.9, roughness: 0.2,
      emissive: 0x001133, emissiveIntensity: 0.2
    });
    const jawMesh = new THREE.Mesh(jawGeo, jawMat);
    jawMesh.position.set(0, -0.2, 0.4);
    jawGroup.position.set(0, -1.0, 1.2);
    jawGroup.add(jawMesh);
    headGroup.add(jawGroup);
    jawGroupRef.current = jawGroup;

    // ==========================================
    // HOLOGRAPHIC BRAIN
    // ==========================================
    const brainGroup = new THREE.Group();
    headGroup.add(brainGroup);
    const brainNodes = [];
    const brainNodeCount = 80;
    const brainNodeGeo = new THREE.SphereGeometry(0.06, 8, 8);
    const brainNodeMat = new THREE.MeshBasicMaterial({ color: 0x00d4ff });

    for (let i = 0; i < brainNodeCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 0.8 + Math.random() * 0.4;
      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta) * 0.8;
      const z = r * Math.cos(phi) * 0.9;
      const node = new THREE.Mesh(brainNodeGeo, brainNodeMat.clone());
      node.position.set(x, y, z);
      node.userData = {
        basePos: new THREE.Vector3(x, y, z),
        activity: Math.random(),
        phase: Math.random() * Math.PI * 2
      };
      brainGroup.add(node);
      brainNodes.push(node);
    }
    brainNodesRef.current = brainNodes;

    const brainLines = [];
    for (let i = 0; i < brainNodes.length; i++) {
      for (let j = i + 1; j < brainNodes.length; j++) {
        const dist = brainNodes[i].position.distanceTo(brainNodes[j].position);
        if (dist < 0.6) {
          const lineGeo = new THREE.BufferGeometry().setFromPoints([
            brainNodes[i].position, brainNodes[j].position
          ]);
          const lineMat = new THREE.LineBasicMaterial({
            color: 0x00d4ff, transparent: true, opacity: 0.1
          });
          const line = new THREE.Line(lineGeo, lineMat);
          brainGroup.add(line);
          brainLines.push({ line, start: brainNodes[i], end: brainNodes[j], baseOpacity: 0.1 });
        }
      }
    }
    brainLinesRef.current = brainLines;

    // ==========================================
    // NEURAL NETWORK
    // ==========================================
    const neuralNetwork = new THREE.Group();
    scene.add(neuralNetwork);
    neuralNetworkRef.current = neuralNetwork;

    const nodeCount = 150;
    const nodes = [];
    const nodeGeo = new THREE.SphereGeometry(0.04, 8, 8);
    const nodeMat = new THREE.MeshBasicMaterial({ color: 0x00d4ff });

    for (let i = 0; i < nodeCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 2.5 + Math.random() * 2.5;
      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta);
      const z = r * Math.cos(phi);
      const node = new THREE.Mesh(nodeGeo, nodeMat.clone());
      node.position.set(x, y, z);
      node.userData = {
        basePos: new THREE.Vector3(x, y, z),
        activity: 0, targetActivity: 0,
        connections: [], phase: Math.random() * Math.PI * 2
      };
      neuralNetwork.add(node);
      nodes.push(node);
    }
    nodesRef.current = nodes;

    const connections = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dist = nodes[i].position.distanceTo(nodes[j].position);
        if (dist < 1.8) {
          const lineGeo = new THREE.BufferGeometry().setFromPoints([
            nodes[i].position, nodes[j].position
          ]);
          const lineMat = new THREE.LineBasicMaterial({
            color: 0x00d4ff, transparent: true, opacity: 0.08
          });
          const line = new THREE.Line(lineGeo, lineMat);
          neuralNetwork.add(line);
          const conn = { line, start: nodes[i], end: nodes[j], packets: [], baseOpacity: 0.08 };
          connections.push(conn);
          nodes[i].userData.connections.push(conn);
          nodes[j].userData.connections.push(conn);
        }
      }
    }
    connectionsRef.current = connections;

    // Packet geometry/material (reused)
    packetGeoRef.current = new THREE.SphereGeometry(0.06, 8, 8);
    packetMatRef.current = new THREE.MeshBasicMaterial({ color: 0xffffff });

    // ==========================================
    // PARTICLE FIELD
    // ==========================================
    const particleCount = 8000;
    const particlesGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleVelocities = [];
    const particlePhases = [];

    for (let i = 0; i < particleCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 2 + Math.random() * 6;
      particlePositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      particlePositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      particlePositions[i * 3 + 2] = r * Math.cos(phi);
      particleVelocities.push({ x: (Math.random() - 0.5) * 0.01, y: (Math.random() - 0.5) * 0.01, z: (Math.random() - 0.5) * 0.01 });
      particlePhases.push(Math.random() * Math.PI * 2);
    }
    particlesGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particlesGeoRef.current = particlesGeo;
    particleVelocitiesRef.current = particleVelocities;
    particlePhasesRef.current = particlePhases;

    const particlesMat = new THREE.PointsMaterial({
      color: 0x00d4ff, size: 0.03, transparent: true, opacity: 0.6,
      blending: THREE.AdditiveBlending, sizeAttenuation: true
    });
    particlesMatRef.current = particlesMat;
    const particleSystem = new THREE.Points(particlesGeo, particlesMat);
    scene.add(particleSystem);

    // Grid
    const gridHelper = new THREE.GridHelper(30, 30, 0x001133, 0x000811);
    gridHelper.position.y = -5;
    scene.add(gridHelper);

    // ==========================================
    // ANIMATION LOOP
    // ==========================================
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate);
      timeRef.current += 0.016;
      const time = timeRef.current;
      const state = stateRef.current;

      // Update brain
      const intensity = state === STATE.THINKING ? 2 : state === STATE.TOOL_CALL ? 3 : state === STATE.SPEAKING ? 1.5 : 0.5;
      brainNodes.forEach(node => {
        const data = node.userData;
        data.activity += (Math.random() - 0.5) * 0.1 * intensity;
        data.activity = Math.max(0, Math.min(1, data.activity));
        const glow = data.activity * intensity;
        node.material.color.setHSL(0.55, 1, 0.3 + glow * 0.7);
        node.scale.setScalar(1 + glow * 0.5);
        if (glow > 0.5) {
          node.position.x = data.basePos.x + Math.sin(time * 5 + data.phase) * 0.02 * glow;
          node.position.y = data.basePos.y + Math.cos(time * 5 + data.phase) * 0.02 * glow;
        }
      });
      brainLines.forEach(({ line, start, end }) => {
        const avg = (start.userData.activity + end.userData.activity) / 2;
        line.material.opacity = 0.1 + avg * 0.5;
      });

      // Update neural network
      let activeCount = 0;
      nodes.forEach(node => {
        const data = node.userData;
        data.targetActivity *= 0.95;
        data.activity += (data.targetActivity - data.activity) * 0.1;
        if (data.activity > 0.1) activeCount++;
        let hue = 0.55;
        if (state === STATE.LISTENING) hue = 0.4;
        if (state === STATE.THINKING) hue = 0.85;
        if (state === STATE.TOOL_CALL) hue = 0.08;
        if (state === STATE.SPEAKING) hue = 0;
        const brightness = 0.2 + data.activity * 2;
        node.material.color.setHSL(hue, 1, brightness);
        node.scale.setScalar(1 + data.activity * 2);
        const driftSpeed = 0.1 + data.activity * 0.5;
        node.position.x = data.basePos.x + Math.sin(time * driftSpeed + data.phase) * 0.1;
        node.position.y = data.basePos.y + Math.cos(time * driftSpeed + data.phase) * 0.1;
        node.position.z = data.basePos.z + Math.sin(time * driftSpeed * 0.7 + data.phase) * 0.1;
      });
      activeNodeCountRef.current = activeCount;

      connections.forEach(conn => {
        const avgActivity = (conn.start.userData.activity + conn.end.userData.activity) / 2;
        conn.line.material.opacity = conn.baseOpacity + avgActivity * 0.5;
        const positions = conn.line.geometry.attributes.position.array;
        positions[0] = conn.start.position.x; positions[1] = conn.start.position.y; positions[2] = conn.start.position.z;
        positions[3] = conn.end.position.x; positions[4] = conn.end.position.y; positions[5] = conn.end.position.z;
        conn.line.geometry.attributes.position.needsUpdate = true;
        if (avgActivity > 0.3 && Math.random() < 0.02 * neuralActivityRef.current) {
          spawnPacket(conn);
        }
      });

      connections.forEach(conn => {
        conn.packets = conn.packets.filter(packet => {
          packet.userData.progress += packet.userData.speed * (1 + neuralActivityRef.current);
          if (packet.userData.progress >= 1) {
            conn.end.userData.targetActivity = 1;
            neuralNetwork.remove(packet);
            return false;
          }
          const start = conn.start.position;
          const end = conn.end.position;
          packet.position.lerpVectors(start, end, packet.userData.progress);
          packet.scale.setScalar(1 + Math.sin(packet.userData.progress * Math.PI) * 0.5);
          return true;
        });
      });

      // Update particles
      const positions = particlesGeo.attributes.position.array;
      const stateColor = new THREE.Color();
      switch(state) {
        case STATE.IDLE: stateColor.setHex(0x00d4ff); break;
        case STATE.LISTENING: stateColor.setHex(0x00ff88); break;
        case STATE.THINKING: stateColor.setHex(0xff00ff); break;
        case STATE.TOOL_CALL: stateColor.setHex(0xffa500); break;
        case STATE.SPEAKING: stateColor.setHex(0xffffff); break;
      }
      particlesMat.color.lerp(stateColor, 0.05);

      for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3;
        const vel = particleVelocities[i];
        const phase = particlePhases[i];
        positions[i3] += vel.x; positions[i3 + 1] += vel.y; positions[i3 + 2] += vel.z;

        if (state === STATE.THINKING) {
          const x = positions[i3], y = positions[i3 + 1], z = positions[i3 + 2];
          const dist = Math.sqrt(x*x + y*y + z*z);
          if (dist > 3) { positions[i3] -= x * 0.002; positions[i3 + 1] -= y * 0.002; positions[i3 + 2] -= z * 0.002; }
          positions[i3] += Math.sin(time * 3 + phase) * 0.02;
          positions[i3 + 1] += Math.cos(time * 3 + phase) * 0.02;
        } else if (state === STATE.SPEAKING) {
          const x = positions[i3], y = positions[i3 + 1], z = positions[i3 + 2];
          const dist = Math.sqrt(x*x + y*y + z*z);
          if (dist < 5) { positions[i3] += x * 0.005; positions[i3 + 1] += y * 0.005; positions[i3 + 2] += z * 0.005; }
        } else if (state === STATE.LISTENING) {
          const x = positions[i3], z = positions[i3 + 2];
          positions[i3] = x * Math.cos(0.01) - z * Math.sin(0.01);
          positions[i3 + 2] = x * Math.sin(0.01) + z * Math.cos(0.01);
        }

        const bound = 8;
        if (Math.abs(positions[i3]) > bound) positions[i3] *= -0.9;
        if (Math.abs(positions[i3 + 1]) > bound) positions[i3 + 1] *= -0.9;
        if (Math.abs(positions[i3 + 2]) > bound) positions[i3 + 2] *= -0.9;
      }
      particlesGeo.attributes.position.needsUpdate = true;

      // Update head
      const targetX = mouseRef.current.x * 0.3;
      const targetY = -mouseRef.current.y * 0.3;
      if (leftPupilRef.current) {
        leftPupilRef.current.position.x += (targetX - leftPupilRef.current.position.x) * 0.1;
        leftPupilRef.current.position.y += (targetY - leftPupilRef.current.position.y) * 0.1;
      }
      if (rightPupilRef.current) {
        rightPupilRef.current.position.x += (targetX - rightPupilRef.current.position.x) * 0.1;
        rightPupilRef.current.position.y += (targetY - rightPupilRef.current.position.y) * 0.1;
      }
      if (headGroupRef.current) {
        headGroupRef.current.rotation.y += (mouseRef.current.x * 0.2 - headGroupRef.current.rotation.y) * 0.05;
        headGroupRef.current.rotation.x += (-mouseRef.current.y * 0.1 - headGroupRef.current.rotation.x) * 0.05;
      }
      if (state === STATE.IDLE && headGroupRef.current) {
        headGroupRef.current.scale.setScalar(1 + Math.sin(time * 0.5) * 0.005);
        if (wireMeshRef.current) wireMeshRef.current.rotation.y += 0.001;
      }

      // Emissive pulse
      const targetEmissive = state === STATE.IDLE ? 0.2 : state === STATE.LISTENING ? 0.4 : state === STATE.THINKING ? 0.8 + Math.sin(time * 10) * 0.3 : state === STATE.TOOL_CALL ? 0.6 + Math.sin(time * 15) * 0.4 : 0.5 + Math.sin(time * 8) * 0.2;
      if (headMaterialRef.current) {
        headMaterialRef.current.emissiveIntensity += (targetEmissive - headMaterialRef.current.emissiveIntensity) * 0.1;
      }
      const targetLight = state === STATE.THINKING ? 2 : state === STATE.TOOL_CALL ? 3 : state === STATE.SPEAKING ? 1.5 : 0.3;
      if (brainLightRef.current) {
        brainLightRef.current.intensity += (targetLight - brainLightRef.current.intensity) * 0.1;
      }

      // Camera drift
      if (cameraRef.current) {
        cameraRef.current.position.x += (mouseRef.current.x * 0.5 - cameraRef.current.position.x) * 0.02;
        cameraRef.current.position.y += (-mouseRef.current.y * 0.3 - cameraRef.current.position.y) * 0.02;
        cameraRef.current.lookAt(0, 0, 0);
      }

      // Metrics decay
      neuralActivityRef.current *= 0.98;
      tokenVelocityRef.current *= 0.95;

      // Update DOM nodes directly to prevent state thrashing and re-renders
      if (Math.floor(time * 10) % 5 === 0) {
        if (loadMetricRef.current) loadMetricRef.current.textContent = `${Math.floor(neuralActivityRef.current * 100)}%`;
        if (velocityMetricRef.current) velocityMetricRef.current.textContent = `${Math.floor(tokenVelocityRef.current)} t/s`;
        if (nodesMetricRef.current) nodesMetricRef.current.textContent = `${activeNodeCountRef.current}`;
        if (fluxMetricRef.current) fluxMetricRef.current.textContent = `${(Math.sin(time) * 0.5 + 0.5).toFixed(2)}`;
      }

      composer.render();
    };

    animate();

    // Resize handler
    const handleResize = () => {
      if (!containerRef.current || !cameraRef.current || !rendererRef.current || !composerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
      composerRef.current.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Mouse tracking
    const handleMouseMove = (e) => {
      mouseRef.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouseRef.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    document.addEventListener('mousemove', handleMouseMove);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('mousemove', handleMouseMove);
      if (rendererRef.current && containerRef.current) {
        containerRef.current.removeChild(rendererRef.current.domElement);
      }
      rendererRef.current?.dispose();
    };
  }, []);

  // ==========================================
  // HELPERS
  // ==========================================
  const spawnPacket = useCallback((conn, color = 0xffffff) => {
    if (!packetGeoRef.current || !packetMatRef.current || !neuralNetworkRef.current) return;
    const packet = new THREE.Mesh(packetGeoRef.current, packetMatRef.current.clone());
    packet.material.color.setHex(color);
    packet.userData = { conn, progress: 0, speed: 0.02 + Math.random() * 0.03 };
    neuralNetworkRef.current.add(packet);
    conn.packets.push(packet);
  }, []);

  const spawnRandomPackets = useCallback((count, color) => {
    const conns = connectionsRef.current;
    if (conns.length === 0) return;
    for (let i = 0; i < count; i++) {
      const conn = conns[Math.floor(Math.random() * conns.length)];
      spawnPacket(conn, color);
    }
  }, [spawnPacket]);

  const activateRandomNodes = useCallback((count) => {
    const nodes = nodesRef.current;
    if (nodes.length === 0) return;
    for (let i = 0; i < count; i++) {
      const idx = Math.floor(Math.random() * nodes.length);
      nodes[idx].userData.targetActivity = 1;
    }
  }, []);

  const typeThought = useCallback((text) => {
    if (typingIntervalRef.current) clearInterval(typingIntervalRef.current);
    setThoughtText('');
    let i = 0;
    typingIntervalRef.current = setInterval(() => {
      if (i >= text.length) {
        clearInterval(typingIntervalRef.current);
        return;
      }
      setThoughtText(prev => prev + text[i]);
      i++;
    }, 30);
  }, []);

  // ==========================================
  // INPUT HANDLING
  // ==========================================
  const handleSend = useCallback(() => {
    if (!userInput.trim() || !socketRef.current) return;
    // RUTH-V3 backend listens for 'user_input' (backend/server.py user_input handler)
    socketRef.current.emit('user_input', { text: userInput.trim() });
    setUserInput('');
  }, [userInput]);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter') handleSend();
  }, [handleSend]);

  // Speech Recognition
  const toggleMic = useCallback(() => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) return;

    if (isMicActive && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsMicActive(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setIsMicActive(true);
      setCurrentState(STATE.LISTENING);
    };

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results).map(r => r[0].transcript).join('');
      setUserInput(transcript);
    };

    recognition.onend = () => {
      setIsMicActive(false);
      if (userInput.trim()) {
        socketRef.current?.emit('user_input', { text: userInput.trim(), source: 'voice' });
        setUserInput('');
      }
    };

    recognition.start();
  }, [isMicActive, userInput]);

  // Cleanup typing interval
  useEffect(() => {
    return () => {
      if (typingIntervalRef.current) clearInterval(typingIntervalRef.current);
      if (toolTimeoutRef.current) clearTimeout(toolTimeoutRef.current);
    };
  }, []);

  // ==========================================
  // RENDER
  // ==========================================
  const getStatusColor = () => {
    switch(currentState) {
      case STATE.IDLE: return '#00d4ff';
      case STATE.LISTENING: return '#00ff88';
      case STATE.THINKING: return '#ff00ff';
      case STATE.TOOL_CALL: return '#ffa500';
      case STATE.SPEAKING: return '#ffffff';
      default: return '#00d4ff';
    }
  };

  const getStatusText = () => {
    switch(currentState) {
      case STATE.IDLE: return 'System Online';
      case STATE.LISTENING: return 'Listening...';
      case STATE.THINKING: return 'Processing...';
      case STATE.TOOL_CALL: return 'Tool Execution';
      case STATE.SPEAKING: return 'Responding...';
      default: return 'System Online';
    }
  };

  return (
    <div className="neural-avatar-container">
      <div ref={containerRef} className="canvas-wrapper" />

      {/* UI Overlay */}
      <div className="ui-layer">
        {/* Top Bar */}
        <div className="top-bar">
          <div className="brand">
            R.U.T.H.<span>NEURAL</span> v3.0
            <span className={`connection-dot ${isConnected ? 'connected' : ''}`} />
          </div>
          <div className="status-indicator" style={{ borderColor: getStatusColor() + '40' }}>
            <div className="status-dot" style={{ 
              background: getStatusColor(), 
              boxShadow: `0 0 10px ${getStatusColor()}, 0 0 20px ${getStatusColor()}40` 
            }} />
            <span>{getStatusText()}</span>
          </div>
        </div>

        {/* Thought Stream */}
        <div className={`thought-stream ${currentState === STATE.THINKING || currentState === STATE.SPEAKING || currentState === STATE.TOOL_CALL ? 'active' : ''}`}>
          <div className="thought-label">Neural Activity</div>
          <div className="thought-text">
            {thoughtText}
            {(currentState === STATE.THINKING || currentState === STATE.SPEAKING) && (
              <span className="cursor-blink" />
            )}
          </div>
        </div>

        {/* Tool Notification */}
        {toolNotification && (
          <div className="tool-notification active" style={{ borderColor: toolNotification.color + '40' }}>
            <div className="tool-icon" style={{ 
              background: toolNotification.color + '15', 
              borderColor: toolNotification.color + '40',
              color: toolNotification.color 
            }}>
              {toolNotification.icon}
            </div>
            <div className="tool-info">
              <div className="tool-name" style={{ color: toolNotification.color }}>{toolNotification.name}</div>
              <div className="tool-desc">{toolNotification.desc}</div>
            </div>
          </div>
        )}

        {/* Left Panel - Metrics */}
        <div className="side-panel left-panel">
          <div className="panel-box">
            <div className="panel-title">Neural Metrics</div>
            <div className="metric-row">
              <span className="metric-label">Synaptic Load</span>
              <span className="metric-value" ref={loadMetricRef}>0%</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Token Velocity</span>
              <span className="metric-value" ref={velocityMetricRef}>0 t/s</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Active Nodes</span>
              <span className="metric-value" ref={nodesMetricRef}>0</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Neural Flux</span>
              <span className="metric-value" ref={fluxMetricRef}>0.00</span>
            </div>
          </div>
        </div>

        {/* Right Panel - Tools */}
        <div className="side-panel right-panel">
          <div className="panel-box">
            <div className="panel-title">Connected Tools</div>
            {Object.entries(TOOL_REGISTRY).slice(0, 8).map(([key, tool]) => (
              <div key={key} className={`tool-item ${activeTools.has(key) ? 'active' : ''}`}>
                <div className="tool-status" style={{
                  background: activeTools.has(key) ? tool.color : 'rgba(255,255,255,0.2)',
                  boxShadow: activeTools.has(key) ? `0 0 8px ${tool.color}` : 'none'
                }} />
                <span>{tool.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Controls */}
        <div className="bottom-controls">
          <div className="input-container">
            <input
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask RUTH anything, or click the mic..."
              className="user-input"
            />
            <button 
              className={`control-btn ${isMicActive ? 'active' : ''}`}
              onClick={toggleMic}
              title="Voice Input"
            >
              🎤
            </button>
            <button className="control-btn send-btn" onClick={handleSend} title="Send">
              →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
