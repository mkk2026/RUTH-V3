import React, { useState, useRef, useEffect } from 'react';
import {
    X,
    MessageCircle,
    Send,
    Hash,
    MessageSquare,
    Phone,
    Shield,
    Wifi,
    WifiOff,
    Eye,
    EyeOff,
    Save,
} from 'lucide-react';

const PLATFORMS = [
    {
        id: 'telegram',
        name: 'Telegram',
        icon: Send,
        color: 'text-blue-400',
        fields: [{ key: 'bot_token', label: 'Bot Token', type: 'password' }],
    },
    {
        id: 'discord',
        name: 'Discord',
        icon: Hash,
        color: 'text-indigo-400',
        fields: [{ key: 'bot_token', label: 'Bot Token', type: 'password' }],
    },
    {
        id: 'slack',
        name: 'Slack',
        icon: MessageSquare,
        color: 'text-green-400',
        fields: [
            { key: 'bot_token', label: 'Bot Token', type: 'password' },
            { key: 'channel_id', label: 'Channel ID', type: 'text' },
        ],
    },
    {
        id: 'whatsapp',
        name: 'WhatsApp',
        icon: Phone,
        color: 'text-emerald-400',
        fields: [
            { key: 'api_key', label: 'API Key', type: 'password' },
            { key: 'phone_number', label: 'Phone Number', type: 'text' },
        ],
    },
    {
        id: 'signal',
        name: 'Signal',
        icon: Shield,
        color: 'text-blue-300',
        fields: [
            { key: 'phone_number', label: 'Phone Number', type: 'text' },
        ],
    },
];

const MessagingSettings = ({ socket, onClose }) => {
    const [platformStatus, setPlatformStatus] = useState(() =>
        PLATFORMS.reduce((acc, p) => {
            acc[p.id] = { connected: false, loading: false, config: {} };
            return acc;
        }, {})
    );
    const [expandedPlatform, setExpandedPlatform] = useState(null);
    const [visibleFields, setVisibleFields] = useState({});
    const [position, setPosition] = useState({
        x: Math.max(60, window.innerWidth / 2 - 240),
        y: Math.max(40, window.innerHeight / 2 - 300),
    });
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 });

    useEffect(() => {
        socket.emit('list_messaging_platforms');

        const handlePlatformList = (data) => {
            if (!data) return;
            setPlatformStatus((prev) => {
                const next = { ...prev };
                const items = Array.isArray(data) ? data : Object.entries(data).map(([id, v]) => ({ id, ...v }));
                items.forEach((item) => {
                    if (next[item.id]) {
                        next[item.id] = {
                            connected: item.connected || false,
                            loading: false,
                            config: item.config || {},
                        };
                    }
                });
                return next;
            });
        };

        const handlePlatformUpdate = (data) => {
            if (!data || !data.id) return;
            setPlatformStatus((prev) => ({
                ...prev,
                [data.id]: {
                    connected: data.connected || false,
                    loading: false,
                    config: data.config || prev[data.id]?.config || {},
                },
            }));
        };

        socket.on('messaging_platform_list', handlePlatformList);
        socket.on('messaging_platform_update', handlePlatformUpdate);

        return () => {
            socket.off('messaging_platform_list', handlePlatformList);
            socket.off('messaging_platform_update', handlePlatformUpdate);
        };
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

    const handleToggleConnection = (platformId) => {
        const current = platformStatus[platformId];
        if (!current) return;

        setPlatformStatus((prev) => ({
            ...prev,
            [platformId]: { ...prev[platformId], loading: true },
        }));

        if (current.connected) {
            socket.emit('disconnect_platform', { id: platformId });
        } else {
            socket.emit('connect_platform', {
                id: platformId,
                config: current.config,
            });
        }
    };

    const handleConfigChange = (platformId, fieldKey, value) => {
        setPlatformStatus((prev) => ({
            ...prev,
            [platformId]: {
                ...prev[platformId],
                config: { ...prev[platformId].config, [fieldKey]: value },
            },
        }));
    };

    const handleSaveConfig = (platformId) => {
        const current = platformStatus[platformId];
        if (!current) return;
        socket.emit('update_platform_config', {
            id: platformId,
            config: current.config,
        });
    };

    const toggleFieldVisibility = (platformId, fieldKey) => {
        const key = `${platformId}.${fieldKey}`;
        setVisibleFields((prev) => ({ ...prev, [key]: !prev[key] }));
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose();
    };

    const connectedCount = Object.values(platformStatus).filter(
        (s) => s.connected
    ).length;

    return (
        <div
            className="fixed bg-black/50 backdrop-blur-xl border border-amber-500/20 rounded-xl shadow-2xl overflow-hidden z-50"
            style={{ left: position.x, top: position.y, width: 480 }}
            onMouseDown={handleDragStart}
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-label="Messaging Settings"
            tabIndex={-1}
        >
            <div
                data-drag-handle
                className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 cursor-grab active:cursor-grabbing select-none"
            >
                <div className="flex items-center gap-2">
                    <MessageCircle size={16} className="text-amber-400" />
                    <h2 className="text-amber-400 font-bold text-sm uppercase tracking-wider font-mono">
                        Messaging
                    </h2>
                    <span className="text-[10px] text-amber-600 font-mono ml-1">
                        {connectedCount}/{PLATFORMS.length} active
                    </span>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-red-400"
                    aria-label="Close messaging settings"
                >
                    <X size={16} />
                </button>
            </div>

            <div className="p-4 max-h-[70vh] overflow-y-auto custom-scrollbar">
                <div className="space-y-3">
                    {PLATFORMS.map((platform) => {
                        const Icon = platform.icon;
                        const status = platformStatus[platform.id] || {
                            connected: false,
                            loading: false,
                            config: {},
                        };
                        const isExpanded = expandedPlatform === platform.id;

                        return (
                            <div
                                key={platform.id}
                                className={`rounded-lg border transition-all duration-200 ${
                                    status.connected
                                        ? 'bg-amber-900/10 border-amber-500/30'
                                        : 'bg-gray-900/50 border-amber-900/20'
                                }`}
                            >
                                <div
                                    className="flex items-center justify-between p-3 cursor-pointer"
                                    onClick={() =>
                                        setExpandedPlatform(
                                            isExpanded ? null : platform.id
                                        )
                                    }
                                    role="button"
                                    tabIndex={0}
                                    aria-expanded={isExpanded}
                                    aria-label={`${platform.name} configuration`}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            setExpandedPlatform(
                                                isExpanded ? null : platform.id
                                            );
                                        }
                                    }}
                                >
                                    <div className="flex items-center gap-3">
                                        <Icon size={20} className={platform.color} />
                                        <div>
                                            <h3 className="text-sm font-bold text-amber-100 font-mono">
                                                {platform.name}
                                            </h3>
                                            <span
                                                className={`text-[10px] font-mono flex items-center gap-1 ${
                                                    status.connected
                                                        ? 'text-green-400'
                                                        : 'text-gray-500'
                                                }`}
                                            >
                                                {status.connected ? (
                                                    <Wifi size={10} />
                                                ) : (
                                                    <WifiOff size={10} />
                                                )}
                                                {status.connected
                                                    ? 'Connected'
                                                    : 'Disconnected'}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div
                                            className={`w-2 h-2 rounded-full ${
                                                status.connected
                                                    ? 'bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.5)]'
                                                    : 'bg-gray-600'
                                            }`}
                                        />
                                    </div>
                                </div>

                                {isExpanded && (
                                    <div className="px-3 pb-3 border-t border-amber-900/20 pt-3">
                                        <div className="space-y-2 mb-3">
                                            {platform.fields.map((field) => {
                                                const visKey = `${platform.id}.${field.key}`;
                                                const isVisible =
                                                    visibleFields[visKey] || false;
                                                const isPassword =
                                                    field.type === 'password';

                                                return (
                                                    <div key={field.key}>
                                                        <label className="text-[10px] text-amber-500/60 uppercase font-mono block mb-1">
                                                            {field.label}
                                                        </label>
                                                        <div className="flex items-center gap-1">
                                                            <input
                                                                type={
                                                                    isPassword && !isVisible
                                                                        ? 'password'
                                                                        : 'text'
                                                                }
                                                                value={
                                                                    status.config[field.key] || ''
                                                                }
                                                                onChange={(e) =>
                                                                    handleConfigChange(
                                                                        platform.id,
                                                                        field.key,
                                                                        e.target.value
                                                                    )
                                                                }
                                                                placeholder={field.label}
                                                                className="flex-1 bg-gray-900 border border-amber-800 rounded px-3 py-1.5 text-xs text-amber-100 placeholder-gray-600 focus:border-amber-400 outline-none font-mono"
                                                                aria-label={field.label}
                                                            />
                                                            {isPassword && (
                                                                <button
                                                                    onClick={() =>
                                                                        toggleFieldVisibility(
                                                                            platform.id,
                                                                            field.key
                                                                        )
                                                                    }
                                                                    className="p-1.5 text-gray-500 hover:text-amber-400 transition-colors"
                                                                    aria-label={
                                                                        isVisible
                                                                            ? 'Hide field'
                                                                            : 'Show field'
                                                                    }
                                                                >
                                                                    {isVisible ? (
                                                                        <EyeOff size={14} />
                                                                    ) : (
                                                                        <Eye size={14} />
                                                                    )}
                                                                </button>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() =>
                                                    handleSaveConfig(platform.id)
                                                }
                                                className="flex items-center gap-1 px-3 py-1.5 bg-amber-900/30 border border-amber-500/30 rounded text-[11px] font-mono text-amber-300 hover:bg-amber-500/20 hover:border-amber-500 transition-all"
                                                aria-label={`Save ${platform.name} config`}
                                            >
                                                <Save size={12} />
                                                Save
                                            </button>
                                            <button
                                                onClick={() =>
                                                    handleToggleConnection(platform.id)
                                                }
                                                disabled={status.loading}
                                                className={`flex-1 py-1.5 rounded text-[11px] font-mono uppercase tracking-wider transition-all ${
                                                    status.loading
                                                        ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                                                        : status.connected
                                                        ? 'bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20'
                                                        : 'bg-green-500/10 border border-green-500/30 text-green-400 hover:bg-green-500/20'
                                                }`}
                                                aria-label={`${
                                                    status.connected
                                                        ? 'Disconnect'
                                                        : 'Connect'
                                                } ${platform.name}`}
                                            >
                                                {status.loading ? (
                                                    <div className="flex items-center justify-center">
                                                        <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                                    </div>
                                                ) : status.connected ? (
                                                    'Disconnect'
                                                ) : (
                                                    'Connect'
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default MessagingSettings;
