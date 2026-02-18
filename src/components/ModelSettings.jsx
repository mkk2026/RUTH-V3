import React, { useState, useRef, useEffect } from 'react';
import { X, Settings, Save, CheckCircle, XCircle } from 'lucide-react';

const TASKS = [
    { id: 'voice', label: 'Voice' },
    { id: 'cad', label: 'CAD' },
    { id: 'web_agent', label: 'Web Agent' },
    { id: 'chat', label: 'Chat' },
    { id: 'embeddings', label: 'Embeddings' },
    { id: 'general', label: 'General' },
];

const PROVIDERS = ['gemini', 'anthropic', 'openai', 'ollama'];

const API_KEY_LABELS = [
    { key: 'GOOGLE_API_KEY', label: 'Google (Gemini)' },
    { key: 'ANTHROPIC_API_KEY', label: 'Anthropic' },
    { key: 'OPENAI_API_KEY', label: 'OpenAI' },
];

const ModelSettings = ({ socket, onClose, modelConfig }) => {
    const [config, setConfig] = useState(() => {
        const defaults = {};
        TASKS.forEach((t) => {
            defaults[t.id] = {
                provider: 'gemini',
                model: '',
            };
        });
        return modelConfig ? { ...defaults, ...modelConfig } : defaults;
    });
    const [apiKeyStatus, setApiKeyStatus] = useState({});
    const [saving, setSaving] = useState(false);
    const [position, setPosition] = useState({
        x: Math.max(60, window.innerWidth / 2 - 240),
        y: Math.max(40, window.innerHeight / 2 - 300),
    });
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 });

    useEffect(() => {
        if (modelConfig) {
            setConfig((prev) => ({ ...prev, ...modelConfig }));
        }
    }, [modelConfig]);

    useEffect(() => {
        socket.emit('get_api_key_status');

        const handleKeyStatus = (status) => {
            if (status) setApiKeyStatus(status);
        };

        socket.on('api_key_status', handleKeyStatus);
        return () => socket.off('api_key_status', handleKeyStatus);
    }, [socket]);

    const handleDragStart = (e) => {
        if (!e.target.closest('[data-drag-handle]')) return;
        dragRef.current = {
            isDragging: true,
            startX: e.clientX - position.x,
            startY: e.clientY - position.y,
        };

        const handleDragMove = (ev) => {
            if (!dragRef.current.isDragging) return;
            setPosition({
                x: ev.clientX - dragRef.current.startX,
                y: ev.clientY - dragRef.current.startY,
            });
        };

        const handleDragEnd = () => {
            dragRef.current.isDragging = false;
            window.removeEventListener('mousemove', handleDragMove);
            window.removeEventListener('mouseup', handleDragEnd);
        };

        window.addEventListener('mousemove', handleDragMove);
        window.addEventListener('mouseup', handleDragEnd);
    };

    const updateTask = (taskId, field, value) => {
        setConfig((prev) => ({
            ...prev,
            [taskId]: { ...prev[taskId], [field]: value },
        }));
    };

    const handleSave = () => {
        setSaving(true);
        socket.emit('update_settings', { model_config: config });
        setTimeout(() => setSaving(false), 1200);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose();
    };

    return (
        <div
            className="fixed bg-black/50 backdrop-blur-xl border border-amber-500/20 rounded-xl shadow-2xl overflow-hidden z-50"
            style={{ left: position.x, top: position.y, width: 480 }}
            onMouseDown={handleDragStart}
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-label="Model Configuration"
            tabIndex={-1}
        >
            <div
                data-drag-handle
                className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 cursor-grab active:cursor-grabbing select-none"
            >
                <div className="flex items-center gap-2">
                    <Settings size={16} className="text-amber-400" />
                    <h2 className="text-amber-400 font-bold text-sm uppercase tracking-wider font-mono">
                        Model Configuration
                    </h2>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-red-400"
                    aria-label="Close model configuration"
                >
                    <X size={16} />
                </button>
            </div>

            <div className="p-4 max-h-[70vh] overflow-y-auto custom-scrollbar">
                <div className="space-y-3 mb-6">
                    <h3 className="text-amber-400 font-bold text-xs uppercase tracking-wider opacity-80 mb-3">
                        Task Providers
                    </h3>
                    {TASKS.map((task) => (
                        <div
                            key={task.id}
                            className="flex items-center gap-3 bg-gray-900/50 p-3 rounded-lg border border-amber-900/30"
                        >
                            <span className="text-amber-100/80 text-xs font-mono w-20 shrink-0">
                                {task.label}
                            </span>
                            <select
                                value={config[task.id]?.provider || 'gemini'}
                                onChange={(e) => updateTask(task.id, 'provider', e.target.value)}
                                className="bg-gray-900 border border-amber-800 rounded px-2 py-1.5 text-xs text-amber-100 focus:border-amber-400 outline-none font-mono flex-shrink-0"
                                aria-label={`Provider for ${task.label}`}
                            >
                                {PROVIDERS.map((p) => (
                                    <option key={p} value={p}>
                                        {p}
                                    </option>
                                ))}
                            </select>
                            <input
                                type="text"
                                value={config[task.id]?.model || ''}
                                onChange={(e) => updateTask(task.id, 'model', e.target.value)}
                                placeholder="model name"
                                className="flex-1 bg-gray-900 border border-amber-800 rounded px-2 py-1.5 text-xs text-amber-100 placeholder-gray-600 focus:border-amber-400 outline-none font-mono"
                                aria-label={`Model name for ${task.label}`}
                            />
                        </div>
                    ))}
                </div>

                <div className="mb-6">
                    <h3 className="text-amber-400 font-bold text-xs uppercase tracking-wider opacity-80 mb-3">
                        API Key Status
                    </h3>
                    <div className="space-y-2">
                        {API_KEY_LABELS.map((item) => {
                            const isSet = apiKeyStatus[item.key] === true;
                            return (
                                <div
                                    key={item.key}
                                    className="flex items-center justify-between text-xs bg-gray-900/50 p-2.5 rounded-lg border border-amber-900/30"
                                >
                                    <span className="text-amber-100/80 font-mono">{item.label}</span>
                                    <div className="flex items-center gap-1.5">
                                        {isSet ? (
                                            <>
                                                <CheckCircle size={14} className="text-green-400" />
                                                <span className="text-green-400 font-mono">SET</span>
                                            </>
                                        ) : (
                                            <>
                                                <XCircle size={14} className="text-red-400" />
                                                <span className="text-red-400 font-mono">MISSING</span>
                                            </>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <button
                    onClick={handleSave}
                    disabled={saving}
                    className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-mono text-xs uppercase tracking-wider transition-all duration-300
                        ${saving
                            ? 'bg-green-500/20 border border-green-500/40 text-green-400'
                            : 'bg-amber-900/30 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 hover:border-amber-500'
                        }`}
                    aria-label="Save model configuration"
                >
                    <Save size={14} />
                    {saving ? 'Saved' : 'Save Configuration'}
                </button>
            </div>
        </div>
    );
};

export default ModelSettings;
