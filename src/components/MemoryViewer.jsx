import React, { useState, useRef, useEffect } from 'react';
import { X, Brain, Search, Database, Zap, BookOpen } from 'lucide-react';

const TYPE_CONFIG = {
    episodic: { label: 'Episodic', color: 'text-purple-400 bg-purple-500/20 border-purple-500/30', icon: Zap },
    semantic: { label: 'Semantic', color: 'text-blue-400 bg-blue-500/20 border-blue-500/30', icon: Database },
    procedural: { label: 'Procedural', color: 'text-green-400 bg-green-500/20 border-green-500/30', icon: BookOpen },
};

const MemoryViewer = ({ socket, onClose, memoryStats }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [stats, setStats] = useState(
        memoryStats || { episodic: 0, semantic: 0, procedural: 0 }
    );
    const [position, setPosition] = useState({
        x: Math.max(60, window.innerWidth / 2 - 240),
        y: Math.max(40, window.innerHeight / 2 - 280),
    });
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 });
    const resultsEndRef = useRef(null);

    useEffect(() => {
        if (memoryStats) setStats(memoryStats);
    }, [memoryStats]);

    useEffect(() => {
        const handleSearchResults = (data) => {
            setSearching(false);
            if (data && Array.isArray(data.results)) {
                setResults(data.results);
            }
        };

        const handleMemoryStats = (data) => {
            if (data) setStats(data);
        };

        socket.on('memory_search_results', handleSearchResults);
        socket.on('memory_stats', handleMemoryStats);

        return () => {
            socket.off('memory_search_results', handleSearchResults);
            socket.off('memory_stats', handleMemoryStats);
        };
    }, [socket]);

    useEffect(() => {
        if (resultsEndRef.current) {
            resultsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [results]);

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

    const handleSearch = () => {
        if (!query.trim()) return;
        setSearching(true);
        setResults([]);
        socket.emit('search_memory', { query: query.trim() });
    };

    const handleSearchKeyDown = (e) => {
        if (e.key === 'Enter') handleSearch();
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose();
    };

    const formatTimestamp = (ts) => {
        if (!ts) return '';
        const d = new Date(ts);
        return d.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div
            className="fixed bg-black/50 backdrop-blur-xl border border-amber-500/20 rounded-xl shadow-2xl overflow-hidden z-50"
            style={{ left: position.x, top: position.y, width: 480 }}
            onMouseDown={handleDragStart}
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-label="Memory Viewer"
            tabIndex={-1}
        >
            <div
                data-drag-handle
                className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 cursor-grab active:cursor-grabbing select-none"
            >
                <div className="flex items-center gap-2">
                    <Brain size={16} className="text-amber-400" />
                    <h2 className="text-amber-400 font-bold text-sm uppercase tracking-wider font-mono">
                        Memory
                    </h2>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-red-400"
                    aria-label="Close memory viewer"
                >
                    <X size={16} />
                </button>
            </div>

            <div className="p-4">
                <div className="grid grid-cols-3 gap-2 mb-4">
                    {Object.entries(TYPE_CONFIG).map(([type, cfg]) => {
                        const Icon = cfg.icon;
                        return (
                            <div
                                key={type}
                                className="flex flex-col items-center p-3 rounded-lg bg-gray-900/50 border border-amber-900/30"
                            >
                                <Icon size={14} className={cfg.color.split(' ')[0]} />
                                <span className="text-lg font-bold text-amber-100 font-mono mt-1">
                                    {stats[type] || 0}
                                </span>
                                <span className="text-[10px] text-gray-500 font-mono uppercase">
                                    {cfg.label}
                                </span>
                            </div>
                        );
                    })}
                </div>

                <div className="flex items-center gap-2 mb-4">
                    <div className="flex-1 relative">
                        <Search
                            size={14}
                            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-amber-600"
                        />
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleSearchKeyDown}
                            placeholder="Search memories..."
                            className="w-full bg-gray-900 border border-amber-800 rounded-lg pl-8 pr-3 py-2 text-xs text-amber-100 placeholder-gray-600 focus:border-amber-400 outline-none font-mono"
                            aria-label="Search memories"
                        />
                    </div>
                    <button
                        onClick={handleSearch}
                        disabled={searching || !query.trim()}
                        className="px-3 py-2 bg-amber-900/30 border border-amber-500/30 rounded-lg text-xs font-mono text-amber-300 hover:bg-amber-500/20 hover:border-amber-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                        aria-label="Search"
                    >
                        {searching ? (
                            <div className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                        ) : (
                            'Query'
                        )}
                    </button>
                </div>

                <div className="max-h-[45vh] overflow-y-auto custom-scrollbar space-y-2">
                    {searching && (
                        <div className="flex items-center justify-center py-8">
                            <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                            <span className="text-xs text-amber-400 font-mono ml-2 animate-pulse">
                                Searching...
                            </span>
                        </div>
                    )}

                    {!searching && results.length === 0 && query && (
                        <div className="text-center py-8">
                            <p className="text-xs text-gray-500 font-mono">No results found</p>
                        </div>
                    )}

                    {results.map((item, index) => {
                        const typeCfg = TYPE_CONFIG[item.type] || TYPE_CONFIG.semantic;
                        return (
                            <div
                                key={index}
                                className="p-3 bg-gray-900/50 rounded-lg border border-amber-900/30 hover:border-amber-500/20 transition-colors"
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span
                                        className={`text-[10px] font-mono px-2 py-0.5 rounded border ${typeCfg.color}`}
                                    >
                                        {typeCfg.label}
                                    </span>
                                    {item.timestamp && (
                                        <span className="text-[10px] text-gray-600 font-mono">
                                            {formatTimestamp(item.timestamp)}
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs text-amber-100/80 font-mono leading-relaxed break-words">
                                    {item.text || item.content || ''}
                                </p>
                            </div>
                        );
                    })}
                    <div ref={resultsEndRef} />
                </div>
            </div>
        </div>
    );
};

export default MemoryViewer;
