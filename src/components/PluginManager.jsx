import React, { useState, useRef, useEffect } from 'react';
import { X, Puzzle, Package, User, ToggleLeft, ToggleRight } from 'lucide-react';

const PluginManager = ({ socket, onClose, plugins }) => {
    const [localPlugins, setLocalPlugins] = useState(plugins || []);
    const [position, setPosition] = useState({
        x: Math.max(60, window.innerWidth / 2 - 220),
        y: Math.max(40, window.innerHeight / 2 - 260),
    });
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 });

    useEffect(() => {
        if (plugins) setLocalPlugins(plugins);
    }, [plugins]);

    useEffect(() => {
        const handlePluginUpdate = (updated) => {
            if (Array.isArray(updated)) {
                setLocalPlugins(updated);
            }
        };

        socket.on('plugin_list', handlePluginUpdate);
        return () => socket.off('plugin_list', handlePluginUpdate);
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

    const togglePlugin = (pluginName, currentEnabled) => {
        setLocalPlugins((prev) =>
            prev.map((p) =>
                p.name === pluginName ? { ...p, enabled: !currentEnabled } : p
            )
        );
        socket.emit('update_plugin_status', {
            name: pluginName,
            enabled: !currentEnabled,
        });
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose();
    };

    return (
        <div
            className="fixed bg-black/50 backdrop-blur-xl border border-amber-500/20 rounded-xl shadow-2xl overflow-hidden z-50"
            style={{ left: position.x, top: position.y, width: 440 }}
            onMouseDown={handleDragStart}
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-label="Plugin Manager"
            tabIndex={-1}
        >
            <div
                data-drag-handle
                className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 cursor-grab active:cursor-grabbing select-none"
            >
                <div className="flex items-center gap-2">
                    <Puzzle size={16} className="text-amber-400" />
                    <h2 className="text-amber-400 font-bold text-sm uppercase tracking-wider font-mono">
                        Plugins
                    </h2>
                    <span className="text-[10px] text-amber-600 font-mono ml-1">
                        ({localPlugins.length})
                    </span>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-red-400"
                    aria-label="Close plugin manager"
                >
                    <X size={16} />
                </button>
            </div>

            <div className="p-4 max-h-[65vh] overflow-y-auto custom-scrollbar">
                {localPlugins.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                        <Puzzle size={32} className="text-amber-900/50 mb-3" />
                        <p className="text-xs text-gray-500 font-mono">No plugins installed</p>
                    </div>
                )}

                <div className="space-y-3">
                    {localPlugins.map((plugin) => (
                        <div
                            key={plugin.name}
                            className={`p-3 rounded-lg border transition-all duration-200 ${
                                plugin.enabled
                                    ? 'bg-amber-900/10 border-amber-500/30'
                                    : 'bg-gray-900/50 border-amber-900/20 opacity-70'
                            }`}
                        >
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-sm font-bold text-amber-100 font-mono truncate">
                                            {plugin.name}
                                        </span>
                                        {plugin.version && (
                                            <span className="text-[10px] text-amber-600 font-mono bg-amber-900/30 px-1.5 py-0.5 rounded">
                                                v{plugin.version}
                                            </span>
                                        )}
                                    </div>
                                    {plugin.description && (
                                        <p className="text-[11px] text-gray-400 font-mono leading-relaxed mb-2">
                                            {plugin.description}
                                        </p>
                                    )}
                                    <div className="flex items-center gap-3 text-[10px] text-gray-500 font-mono">
                                        {plugin.author && (
                                            <span className="flex items-center gap-1">
                                                <User size={10} />
                                                {plugin.author}
                                            </span>
                                        )}
                                        {typeof plugin.tool_count === 'number' && (
                                            <span className="flex items-center gap-1">
                                                <Package size={10} />
                                                {plugin.tool_count} tool{plugin.tool_count !== 1 ? 's' : ''}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <button
                                    onClick={() => togglePlugin(plugin.name, plugin.enabled)}
                                    className={`shrink-0 mt-0.5 transition-colors duration-200 ${
                                        plugin.enabled ? 'text-amber-400' : 'text-gray-600'
                                    }`}
                                    aria-label={`${plugin.enabled ? 'Disable' : 'Enable'} ${plugin.name}`}
                                >
                                    {plugin.enabled ? (
                                        <ToggleRight size={28} />
                                    ) : (
                                        <ToggleLeft size={28} />
                                    )}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default PluginManager;
