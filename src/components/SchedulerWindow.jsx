import React, { useState, useRef, useEffect } from 'react';
import {
    X,
    Clock,
    Plus,
    Trash2,
    ToggleLeft,
    ToggleRight,
    Play,
    Calendar,
    Timer,
    Repeat,
} from 'lucide-react';

const SCHEDULE_TYPES = [
    { id: 'once', label: 'Once', icon: Play },
    { id: 'interval', label: 'Interval', icon: Timer },
    { id: 'cron', label: 'Cron', icon: Repeat },
];

const SchedulerWindow = ({ socket, onClose, tasks }) => {
    const [localTasks, setLocalTasks] = useState(tasks || []);
    const [showAddForm, setShowAddForm] = useState(false);
    const [newTask, setNewTask] = useState({
        name: '',
        schedule_type: 'once',
        schedule_value: '',
        tool_name: '',
    });
    const [position, setPosition] = useState({
        x: Math.max(60, window.innerWidth / 2 - 260),
        y: Math.max(40, window.innerHeight / 2 - 280),
    });
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 });

    useEffect(() => {
        if (tasks) setLocalTasks(tasks);
    }, [tasks]);

    useEffect(() => {
        socket.emit('list_tasks');

        const handleTaskList = (data) => {
            if (Array.isArray(data)) setLocalTasks(data);
        };

        const handleTaskUpdate = (data) => {
            if (Array.isArray(data)) {
                setLocalTasks(data);
            } else if (data && data.tasks) {
                setLocalTasks(data.tasks);
            }
        };

        socket.on('task_list', handleTaskList);
        socket.on('task_update', handleTaskUpdate);

        return () => {
            socket.off('task_list', handleTaskList);
            socket.off('task_update', handleTaskUpdate);
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

    const handleCreateTask = () => {
        if (!newTask.name.trim() || !newTask.schedule_value.trim()) return;
        socket.emit('create_task', {
            name: newTask.name.trim(),
            schedule_type: newTask.schedule_type,
            schedule_value: newTask.schedule_value.trim(),
            tool_name: newTask.tool_name.trim(),
        });
        setNewTask({ name: '', schedule_type: 'once', schedule_value: '', tool_name: '' });
        setShowAddForm(false);
    };

    const handleToggleTask = (taskId, currentEnabled) => {
        setLocalTasks((prev) =>
            prev.map((t) =>
                t.id === taskId ? { ...t, enabled: !currentEnabled } : t
            )
        );
        socket.emit('toggle_task', { id: taskId, enabled: !currentEnabled });
    };

    const handleDeleteTask = (taskId) => {
        setLocalTasks((prev) => prev.filter((t) => t.id !== taskId));
        socket.emit('delete_task', { id: taskId });
    };

    const formatNextRun = (ts) => {
        if (!ts) return 'N/A';
        const d = new Date(ts);
        return d.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getScheduleIcon = (type) => {
        const match = SCHEDULE_TYPES.find((s) => s.id === type);
        return match ? match.icon : Calendar;
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            if (showAddForm) {
                setShowAddForm(false);
            } else {
                onClose();
            }
        }
    };

    return (
        <div
            className="fixed bg-black/50 backdrop-blur-xl border border-amber-500/20 rounded-xl shadow-2xl overflow-hidden z-50"
            style={{ left: position.x, top: position.y, width: 520 }}
            onMouseDown={handleDragStart}
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-label="Task Scheduler"
            tabIndex={-1}
        >
            <div
                data-drag-handle
                className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 cursor-grab active:cursor-grabbing select-none"
            >
                <div className="flex items-center gap-2">
                    <Clock size={16} className="text-amber-400" />
                    <h2 className="text-amber-400 font-bold text-sm uppercase tracking-wider font-mono">
                        Scheduler
                    </h2>
                    <span className="text-[10px] text-amber-600 font-mono ml-1">
                        ({localTasks.length})
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowAddForm(!showAddForm)}
                        className={`p-1 rounded transition-colors ${
                            showAddForm
                                ? 'bg-amber-500/20 text-amber-400'
                                : 'text-white/50 hover:bg-white/10 hover:text-amber-400'
                        }`}
                        aria-label="Add new task"
                    >
                        <Plus size={16} />
                    </button>
                    <button
                        onClick={onClose}
                        className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-red-400"
                        aria-label="Close scheduler"
                    >
                        <X size={16} />
                    </button>
                </div>
            </div>

            <div className="p-4 max-h-[65vh] overflow-y-auto custom-scrollbar">
                {showAddForm && (
                    <div className="mb-4 p-3 bg-amber-900/10 rounded-lg border border-amber-500/20">
                        <h3 className="text-amber-400 font-bold text-xs uppercase tracking-wider mb-3 font-mono">
                            New Task
                        </h3>
                        <div className="space-y-2">
                            <input
                                type="text"
                                value={newTask.name}
                                onChange={(e) =>
                                    setNewTask((prev) => ({ ...prev, name: e.target.value }))
                                }
                                placeholder="Task name"
                                className="w-full bg-gray-900 border border-amber-800 rounded px-3 py-2 text-xs text-amber-100 placeholder-gray-600 focus:border-amber-400 outline-none font-mono"
                                aria-label="Task name"
                            />
                            <div className="flex gap-2">
                                <select
                                    value={newTask.schedule_type}
                                    onChange={(e) =>
                                        setNewTask((prev) => ({
                                            ...prev,
                                            schedule_type: e.target.value,
                                        }))
                                    }
                                    className="bg-gray-900 border border-amber-800 rounded px-2 py-2 text-xs text-amber-100 focus:border-amber-400 outline-none font-mono"
                                    aria-label="Schedule type"
                                >
                                    {SCHEDULE_TYPES.map((s) => (
                                        <option key={s.id} value={s.id}>
                                            {s.label}
                                        </option>
                                    ))}
                                </select>
                                <input
                                    type="text"
                                    value={newTask.schedule_value}
                                    onChange={(e) =>
                                        setNewTask((prev) => ({
                                            ...prev,
                                            schedule_value: e.target.value,
                                        }))
                                    }
                                    placeholder={
                                        newTask.schedule_type === 'cron'
                                            ? '*/5 * * * *'
                                            : newTask.schedule_type === 'interval'
                                            ? '30m'
                                            : '2026-03-01 09:00'
                                    }
                                    className="flex-1 bg-gray-900 border border-amber-800 rounded px-3 py-2 text-xs text-amber-100 placeholder-gray-600 focus:border-amber-400 outline-none font-mono"
                                    aria-label="Schedule value"
                                />
                            </div>
                            <input
                                type="text"
                                value={newTask.tool_name}
                                onChange={(e) =>
                                    setNewTask((prev) => ({ ...prev, tool_name: e.target.value }))
                                }
                                placeholder="Tool name (e.g. run_web_agent)"
                                className="w-full bg-gray-900 border border-amber-800 rounded px-3 py-2 text-xs text-amber-100 placeholder-gray-600 focus:border-amber-400 outline-none font-mono"
                                aria-label="Tool name"
                            />
                            <div className="flex justify-end gap-2 pt-1">
                                <button
                                    onClick={() => setShowAddForm(false)}
                                    className="px-3 py-1.5 text-xs font-mono text-gray-400 hover:text-white transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleCreateTask}
                                    disabled={!newTask.name.trim() || !newTask.schedule_value.trim()}
                                    className="px-3 py-1.5 bg-amber-900/30 border border-amber-500/30 rounded text-xs font-mono text-amber-300 hover:bg-amber-500/20 hover:border-amber-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    Create
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {localTasks.length === 0 && !showAddForm && (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                        <Clock size={32} className="text-amber-900/50 mb-3" />
                        <p className="text-xs text-gray-500 font-mono">No scheduled tasks</p>
                        <button
                            onClick={() => setShowAddForm(true)}
                            className="mt-3 px-4 py-2 bg-amber-900/30 border border-amber-500/30 rounded-lg text-xs font-mono text-amber-300 hover:bg-amber-500/20 hover:border-amber-500 transition-all"
                        >
                            Add First Task
                        </button>
                    </div>
                )}

                <div className="space-y-2">
                    {localTasks.map((task) => {
                        const ScheduleIcon = getScheduleIcon(task.schedule_type);
                        return (
                            <div
                                key={task.id}
                                className={`p-3 rounded-lg border transition-all duration-200 ${
                                    task.enabled
                                        ? 'bg-gray-900/50 border-amber-900/30 hover:border-amber-500/20'
                                        : 'bg-gray-900/30 border-gray-800/30 opacity-60'
                                }`}
                            >
                                <div className="flex items-center justify-between gap-3">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-sm font-bold text-amber-100 font-mono truncate">
                                                {task.name}
                                            </span>
                                            <span className="flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-900/30 text-amber-500 border border-amber-900/40">
                                                <ScheduleIcon size={10} />
                                                {task.schedule_type}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-3 text-[10px] text-gray-500 font-mono">
                                            <span>
                                                Schedule: {task.schedule_value || 'N/A'}
                                            </span>
                                            {task.next_run && (
                                                <span className="flex items-center gap-1">
                                                    <Calendar size={10} />
                                                    Next: {formatNextRun(task.next_run)}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                        <button
                                            onClick={() =>
                                                handleToggleTask(task.id, task.enabled)
                                            }
                                            className={`transition-colors duration-200 ${
                                                task.enabled
                                                    ? 'text-amber-400'
                                                    : 'text-gray-600'
                                            }`}
                                            aria-label={`${
                                                task.enabled ? 'Disable' : 'Enable'
                                            } ${task.name}`}
                                        >
                                            {task.enabled ? (
                                                <ToggleRight size={24} />
                                            ) : (
                                                <ToggleLeft size={24} />
                                            )}
                                        </button>
                                        <button
                                            onClick={() => handleDeleteTask(task.id)}
                                            className="p-1 rounded text-gray-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                                            aria-label={`Delete ${task.name}`}
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default SchedulerWindow;
