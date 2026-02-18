import React, { useState, useRef, useEffect } from 'react';
import { X, Plug, Mail, Calendar, Github, Webhook, Wifi, WifiOff } from 'lucide-react';

const INTEGRATIONS = [
    { id: 'gmail', name: 'Gmail', icon: Mail, color: 'text-red-400' },
    { id: 'calendar', name: 'Calendar', icon: Calendar, color: 'text-blue-400' },
    { id: 'github', name: 'GitHub', icon: Github, color: 'text-white' },
    { id: 'webhooks', name: 'Webhooks', icon: Webhook, color: 'text-purple-400' },
];

const IntegrationPanel = ({ socket, onClose }) => {
    const [integrations, setIntegrations] = useState(() =>
        INTEGRATIONS.reduce((acc, item) => {
            acc[item.id] = { connected: false, loading: false };
            return acc;
        }, {})
    );
    const [position, setPosition] = useState({
        x: Math.max(60, window.innerWidth / 2 - 260),
        y: Math.max(40, window.innerHeight / 2 - 200),
    });
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 });

    useEffect(() => {
        socket.emit('list_integrations');

        const handleIntegrationList = (data) => {
            if (!data) return;
            setIntegrations((prev) => {
                const next = { ...prev };
                if (Array.isArray(data)) {
                    data.forEach((item) => {
                        if (next[item.id]) {
                            next[item.id] = {
                                connected: item.connected || false,
                                loading: false,
                            };
                        }
                    });
                } else if (typeof data === 'object') {
                    Object.entries(data).forEach(([id, status]) => {
                        if (next[id]) {
                            next[id] = {
                                connected: typeof status === 'boolean' ? status : status?.connected || false,
                                loading: false,
                            };
                        }
                    });
                }
                return next;
            });
        };

        const handleIntegrationUpdate = (data) => {
            if (!data || !data.id) return;
            setIntegrations((prev) => ({
                ...prev,
                [data.id]: {
                    connected: data.connected || false,
                    loading: false,
                },
            }));
        };

        socket.on('integration_list', handleIntegrationList);
        socket.on('integration_update', handleIntegrationUpdate);

        return () => {
            socket.off('integration_list', handleIntegrationList);
            socket.off('integration_update', handleIntegrationUpdate);
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

    const handleToggleConnection = (integrationId) => {
        const current = integrations[integrationId];
        if (!current) return;

        setIntegrations((prev) => ({
            ...prev,
            [integrationId]: { ...prev[integrationId], loading: true },
        }));

        if (current.connected) {
            socket.emit('disconnect_integration', { id: integrationId });
        } else {
            socket.emit('connect_integration', { id: integrationId });
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose();
    };

    const connectedCount = Object.values(integrations).filter((s) => s.connected).length;

    return (
        <div
            className="fixed bg-black/50 backdrop-blur-xl border border-amber-500/20 rounded-xl shadow-2xl overflow-hidden z-50"
            style={{ left: position.x, top: position.y, width: 520 }}
            onMouseDown={handleDragStart}
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-label="Integrations"
            tabIndex={-1}
        >
            <div
                data-drag-handle
                className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 cursor-grab active:cursor-grabbing select-none"
            >
                <div className="flex items-center gap-2">
                    <Plug size={16} className="text-amber-400" />
                    <h2 className="text-amber-400 font-bold text-sm uppercase tracking-wider font-mono">
                        Integrations
                    </h2>
                    <span className="text-[10px] text-amber-600 font-mono ml-1">
                        {connectedCount}/{INTEGRATIONS.length} active
                    </span>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-red-400"
                    aria-label="Close integrations"
                >
                    <X size={16} />
                </button>
            </div>

            <div className="p-4">
                <div className="grid grid-cols-2 gap-3">
                    {INTEGRATIONS.map((integration) => {
                        const Icon = integration.icon;
                        const status = integrations[integration.id] || {
                            connected: false,
                            loading: false,
                        };

                        return (
                            <div
                                key={integration.id}
                                className={`p-4 rounded-lg border transition-all duration-300 ${
                                    status.connected
                                        ? 'bg-amber-900/10 border-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.1)]'
                                        : 'bg-gray-900/50 border-amber-900/20 hover:border-amber-500/20'
                                }`}
                            >
                                <div className="flex items-center justify-between mb-3">
                                    <Icon size={24} className={integration.color} />
                                    <div className="flex items-center gap-1.5">
                                        <div
                                            className={`w-2 h-2 rounded-full transition-colors ${
                                                status.connected
                                                    ? 'bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.5)]'
                                                    : 'bg-gray-600'
                                            }`}
                                        />
                                        {status.connected ? (
                                            <Wifi size={12} className="text-green-400" />
                                        ) : (
                                            <WifiOff size={12} className="text-gray-600" />
                                        )}
                                    </div>
                                </div>

                                <div className="mb-3">
                                    <h3 className="text-sm font-bold text-amber-100 font-mono">
                                        {integration.name}
                                    </h3>
                                    <span
                                        className={`text-[10px] font-mono ${
                                            status.connected
                                                ? 'text-green-400'
                                                : 'text-gray-500'
                                        }`}
                                    >
                                        {status.connected ? 'Connected' : 'Disconnected'}
                                    </span>
                                </div>

                                <button
                                    onClick={() => handleToggleConnection(integration.id)}
                                    disabled={status.loading}
                                    className={`w-full py-1.5 rounded text-[11px] font-mono uppercase tracking-wider transition-all ${
                                        status.loading
                                            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                                            : status.connected
                                            ? 'bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20'
                                            : 'bg-amber-900/30 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 hover:border-amber-500'
                                    }`}
                                    aria-label={`${status.connected ? 'Disconnect' : 'Connect'} ${
                                        integration.name
                                    }`}
                                >
                                    {status.loading ? (
                                        <div className="flex items-center justify-center gap-1">
                                            <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                        </div>
                                    ) : status.connected ? (
                                        'Disconnect'
                                    ) : (
                                        'Connect'
                                    )}
                                </button>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default IntegrationPanel;
