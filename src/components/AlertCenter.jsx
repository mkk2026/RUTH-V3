import React, { useState, useRef, useEffect } from 'react';
import {
    X,
    Bell,
    ShieldAlert,
    Info,
    AlertTriangle,
    XOctagon,
    Plus,
    Trash2,
    ToggleLeft,
    ToggleRight,
} from 'lucide-react';

const SEVERITY_CONFIG = {
    info: { label: 'Info', color: 'text-blue-400 bg-blue-500/20 border-blue-500/30', icon: Info },
    warning: {
        label: 'Warning',
        color: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30',
        icon: AlertTriangle,
    },
    error: {
        label: 'Error',
        color: 'text-red-400 bg-red-500/20 border-red-500/30',
        icon: XOctagon,
    },
    critical: {
        label: 'Critical',
        color: 'text-red-500 bg-red-600/20 border-red-600/30',
        icon: ShieldAlert,
    },
};

const CONDITION_TYPES = ['threshold', 'pattern', 'frequency', 'absence'];
const ACTION_TYPES = ['notify', 'email', 'webhook', 'command'];

const AlertCenter = ({ socket, onClose, notifications, rules }) => {
    const [activeTab, setActiveTab] = useState('notifications');
    const [localNotifications, setLocalNotifications] = useState(notifications || []);
    const [localRules, setLocalRules] = useState(rules || []);
    const [showAddRule, setShowAddRule] = useState(false);
    const [newRule, setNewRule] = useState({
        name: '',
        condition_type: 'threshold',
        action_type: 'notify',
    });
    const [position, setPosition] = useState({
        x: Math.max(60, window.innerWidth / 2 - 240),
        y: Math.max(40, window.innerHeight / 2 - 280),
    });
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 });

    useEffect(() => {
        if (notifications) setLocalNotifications(notifications);
    }, [notifications]);

    useEffect(() => {
        if (rules) setLocalRules(rules);
    }, [rules]);

    useEffect(() => {
        socket.emit('get_notifications');
        socket.emit('get_alert_rules');

        const handleNotifications = (data) => {
            if (Array.isArray(data)) setLocalNotifications(data);
        };

        const handleRules = (data) => {
            if (Array.isArray(data)) setLocalRules(data);
        };

        socket.on('notifications', handleNotifications);
        socket.on('alert_rules', handleRules);

        return () => {
            socket.off('notifications', handleNotifications);
            socket.off('alert_rules', handleRules);
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

    const handleClearAll = () => {
        setLocalNotifications([]);
        socket.emit('clear_notifications');
    };

    const handleAddRule = () => {
        if (!newRule.name.trim()) return;
        socket.emit('add_alert_rule', {
            name: newRule.name.trim(),
            condition_type: newRule.condition_type,
            action_type: newRule.action_type,
        });
        setNewRule({ name: '', condition_type: 'threshold', action_type: 'notify' });
        setShowAddRule(false);
    };

    const handleToggleRule = (ruleId, currentEnabled) => {
        setLocalRules((prev) =>
            prev.map((r) =>
                r.id === ruleId ? { ...r, enabled: !currentEnabled } : r
            )
        );
        socket.emit('toggle_alert_rule', { id: ruleId, enabled: !currentEnabled });
    };

    const formatTimestamp = (ts) => {
        if (!ts) return '';
        const d = new Date(ts);
        return d.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            if (showAddRule) {
                setShowAddRule(false);
            } else {
                onClose();
            }
        }
    };

    const unreadCount = localNotifications.filter((n) => !n.read).length;

    return (
        <div
            className="fixed bg-black/50 backdrop-blur-xl border border-amber-500/20 rounded-xl shadow-2xl overflow-hidden z-50"
            style={{ left: position.x, top: position.y, width: 480 }}
            onMouseDown={handleDragStart}
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-label="Alert Center"
            tabIndex={-1}
        >
            <div
                data-drag-handle
                className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 cursor-grab active:cursor-grabbing select-none"
            >
                <div className="flex items-center gap-2">
                    <Bell size={16} className="text-amber-400" />
                    <h2 className="text-amber-400 font-bold text-sm uppercase tracking-wider font-mono">
                        Alerts
                    </h2>
                    {unreadCount > 0 && (
                        <span className="text-[10px] font-mono bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded-full">
                            {unreadCount}
                        </span>
                    )}
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-red-400"
                    aria-label="Close alert center"
                >
                    <X size={16} />
                </button>
            </div>

            <div className="flex border-b border-amber-500/10">
                <button
                    onClick={() => setActiveTab('notifications')}
                    className={`flex-1 px-4 py-2.5 text-xs font-mono uppercase tracking-wider transition-colors ${
                        activeTab === 'notifications'
                            ? 'text-amber-400 border-b-2 border-amber-400 bg-amber-500/5'
                            : 'text-gray-500 hover:text-gray-300'
                    }`}
                    role="tab"
                    aria-selected={activeTab === 'notifications'}
                >
                    Notifications
                </button>
                <button
                    onClick={() => setActiveTab('rules')}
                    className={`flex-1 px-4 py-2.5 text-xs font-mono uppercase tracking-wider transition-colors ${
                        activeTab === 'rules'
                            ? 'text-amber-400 border-b-2 border-amber-400 bg-amber-500/5'
                            : 'text-gray-500 hover:text-gray-300'
                    }`}
                    role="tab"
                    aria-selected={activeTab === 'rules'}
                >
                    Rules
                </button>
            </div>

            <div className="p-4 max-h-[55vh] overflow-y-auto custom-scrollbar">
                {activeTab === 'notifications' && (
                    <>
                        {localNotifications.length > 0 && (
                            <div className="flex justify-end mb-3">
                                <button
                                    onClick={handleClearAll}
                                    className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono text-gray-500 hover:text-red-400 transition-colors"
                                    aria-label="Clear all notifications"
                                >
                                    <Trash2 size={12} />
                                    Clear All
                                </button>
                            </div>
                        )}

                        {localNotifications.length === 0 && (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <Bell size={32} className="text-amber-900/50 mb-3" />
                                <p className="text-xs text-gray-500 font-mono">
                                    No notifications
                                </p>
                            </div>
                        )}

                        <div className="space-y-2">
                            {localNotifications.map((notif, index) => {
                                const severity =
                                    SEVERITY_CONFIG[notif.severity] || SEVERITY_CONFIG.info;
                                const Icon = severity.icon;
                                return (
                                    <div
                                        key={notif.id || index}
                                        className="p-3 bg-gray-900/50 rounded-lg border border-amber-900/30 hover:border-amber-500/20 transition-colors"
                                    >
                                        <div className="flex items-start gap-2">
                                            <Icon
                                                size={14}
                                                className={`shrink-0 mt-0.5 ${
                                                    severity.color.split(' ')[0]
                                                }`}
                                            />
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center justify-between gap-2 mb-1">
                                                    <span
                                                        className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${severity.color}`}
                                                    >
                                                        {severity.label}
                                                    </span>
                                                    {notif.timestamp && (
                                                        <span className="text-[10px] text-gray-600 font-mono shrink-0">
                                                            {formatTimestamp(notif.timestamp)}
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="text-xs text-amber-100/80 font-mono leading-relaxed break-words">
                                                    {notif.message}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </>
                )}

                {activeTab === 'rules' && (
                    <>
                        <div className="flex justify-end mb-3">
                            <button
                                onClick={() => setShowAddRule(!showAddRule)}
                                className={`flex items-center gap-1 px-2 py-1 text-[10px] font-mono transition-colors ${
                                    showAddRule
                                        ? 'text-amber-400'
                                        : 'text-gray-500 hover:text-amber-400'
                                }`}
                                aria-label="Add alert rule"
                            >
                                <Plus size={12} />
                                Add Rule
                            </button>
                        </div>

                        {showAddRule && (
                            <div className="mb-4 p-3 bg-amber-900/10 rounded-lg border border-amber-500/20">
                                <div className="space-y-2">
                                    <input
                                        type="text"
                                        value={newRule.name}
                                        onChange={(e) =>
                                            setNewRule((prev) => ({
                                                ...prev,
                                                name: e.target.value,
                                            }))
                                        }
                                        placeholder="Rule name"
                                        className="w-full bg-gray-900 border border-amber-800 rounded px-3 py-2 text-xs text-amber-100 placeholder-gray-600 focus:border-amber-400 outline-none font-mono"
                                        aria-label="Rule name"
                                    />
                                    <div className="flex gap-2">
                                        <select
                                            value={newRule.condition_type}
                                            onChange={(e) =>
                                                setNewRule((prev) => ({
                                                    ...prev,
                                                    condition_type: e.target.value,
                                                }))
                                            }
                                            className="flex-1 bg-gray-900 border border-amber-800 rounded px-2 py-2 text-xs text-amber-100 focus:border-amber-400 outline-none font-mono"
                                            aria-label="Condition type"
                                        >
                                            {CONDITION_TYPES.map((c) => (
                                                <option key={c} value={c}>
                                                    {c}
                                                </option>
                                            ))}
                                        </select>
                                        <select
                                            value={newRule.action_type}
                                            onChange={(e) =>
                                                setNewRule((prev) => ({
                                                    ...prev,
                                                    action_type: e.target.value,
                                                }))
                                            }
                                            className="flex-1 bg-gray-900 border border-amber-800 rounded px-2 py-2 text-xs text-amber-100 focus:border-amber-400 outline-none font-mono"
                                            aria-label="Action type"
                                        >
                                            {ACTION_TYPES.map((a) => (
                                                <option key={a} value={a}>
                                                    {a}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="flex justify-end gap-2 pt-1">
                                        <button
                                            onClick={() => setShowAddRule(false)}
                                            className="px-3 py-1.5 text-xs font-mono text-gray-400 hover:text-white transition-colors"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={handleAddRule}
                                            disabled={!newRule.name.trim()}
                                            className="px-3 py-1.5 bg-amber-900/30 border border-amber-500/30 rounded text-xs font-mono text-amber-300 hover:bg-amber-500/20 hover:border-amber-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                        >
                                            Add
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {localRules.length === 0 && !showAddRule && (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <ShieldAlert size={32} className="text-amber-900/50 mb-3" />
                                <p className="text-xs text-gray-500 font-mono">No alert rules</p>
                            </div>
                        )}

                        <div className="space-y-2">
                            {localRules.map((rule) => (
                                <div
                                    key={rule.id}
                                    className={`p-3 rounded-lg border transition-all duration-200 ${
                                        rule.enabled
                                            ? 'bg-gray-900/50 border-amber-900/30 hover:border-amber-500/20'
                                            : 'bg-gray-900/30 border-gray-800/30 opacity-60'
                                    }`}
                                >
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="flex-1 min-w-0">
                                            <span className="text-sm font-bold text-amber-100 font-mono truncate block">
                                                {rule.name}
                                            </span>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-900/30 text-amber-500 border border-amber-900/40">
                                                    {rule.condition_type}
                                                </span>
                                                <span className="text-[10px] text-gray-600 font-mono">
                                                    -&gt;
                                                </span>
                                                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-900/30 text-purple-400 border border-purple-900/40">
                                                    {rule.action_type}
                                                </span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() =>
                                                handleToggleRule(rule.id, rule.enabled)
                                            }
                                            className={`shrink-0 transition-colors duration-200 ${
                                                rule.enabled
                                                    ? 'text-amber-400'
                                                    : 'text-gray-600'
                                            }`}
                                            aria-label={`${
                                                rule.enabled ? 'Disable' : 'Enable'
                                            } rule ${rule.name}`}
                                        >
                                            {rule.enabled ? (
                                                <ToggleRight size={24} />
                                            ) : (
                                                <ToggleLeft size={24} />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default AlertCenter;
