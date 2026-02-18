import React, { useState, useRef, useEffect } from 'react';
import { X, Terminal } from 'lucide-react';

const TerminalWindow = ({ socket, onClose }) => {
    const [input, setInput] = useState('');
    const [output, setOutput] = useState([]);
    const [position, setPosition] = useState({
        x: Math.max(60, window.innerWidth / 2 - 280),
        y: Math.max(40, window.innerHeight / 2 - 220),
    });
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 });
    const outputEndRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        const handleOutput = (data) => {
            if (!data) return;
            const line = typeof data === 'string' ? data : data.output || data.text || '';
            if (line) {
                setOutput((prev) => [...prev, { type: 'output', text: line, ts: Date.now() }]);
            }
        };

        const handleError = (data) => {
            if (!data) return;
            const line = typeof data === 'string' ? data : data.error || data.text || '';
            if (line) {
                setOutput((prev) => [...prev, { type: 'error', text: line, ts: Date.now() }]);
            }
        };

        socket.on('terminal_output', handleOutput);
        socket.on('terminal_error', handleError);

        return () => {
            socket.off('terminal_output', handleOutput);
            socket.off('terminal_error', handleError);
        };
    }, [socket]);

    useEffect(() => {
        if (outputEndRef.current) {
            outputEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [output]);

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

    const handleSend = () => {
        if (!input.trim()) return;
        setOutput((prev) => [
            ...prev,
            { type: 'input', text: `$ ${input}`, ts: Date.now() },
        ]);
        socket.emit('terminal_input', { command: input.trim() });
        setInput('');
    };

    const handleInputKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleSend();
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose();
    };

    const focusInput = () => {
        if (inputRef.current) inputRef.current.focus();
    };

    return (
        <div
            className="fixed bg-black/50 backdrop-blur-xl border border-amber-500/20 rounded-xl shadow-2xl overflow-hidden z-50 flex flex-col"
            style={{ left: position.x, top: position.y, width: 560, height: 400 }}
            onMouseDown={handleDragStart}
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-label="Terminal"
            tabIndex={-1}
        >
            <div
                data-drag-handle
                className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 cursor-grab active:cursor-grabbing select-none shrink-0"
            >
                <div className="flex items-center gap-2">
                    <Terminal size={16} className="text-amber-400" />
                    <h2 className="text-amber-400 font-bold text-sm uppercase tracking-wider font-mono">
                        Terminal
                    </h2>
                    <div className="flex items-center gap-1 ml-2">
                        <div className="w-2 h-2 rounded-full bg-red-500" />
                        <div className="w-2 h-2 rounded-full bg-yellow-500" />
                        <div className="w-2 h-2 rounded-full bg-green-500" />
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-red-400"
                    aria-label="Close terminal"
                >
                    <X size={16} />
                </button>
            </div>

            <div
                className="flex-1 bg-black p-3 overflow-y-auto font-mono text-xs custom-scrollbar"
                onClick={focusInput}
                role="log"
                aria-label="Terminal output"
            >
                <div className="text-green-400/60 mb-2">
                    R.U.T.H. Terminal v3.0 -- Type commands below
                </div>
                {output.map((line, i) => (
                    <div
                        key={i}
                        className={`mb-0.5 break-words leading-relaxed ${
                            line.type === 'input'
                                ? 'text-amber-300'
                                : line.type === 'error'
                                ? 'text-red-400'
                                : 'text-green-400'
                        }`}
                    >
                        {line.text}
                    </div>
                ))}
                <div ref={outputEndRef} />
            </div>

            <div className="shrink-0 bg-black border-t border-amber-900/30 flex items-center px-3 py-2 gap-2">
                <span className="text-green-400 font-mono text-xs select-none">$</span>
                <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleInputKeyDown}
                    placeholder="Enter command..."
                    className="flex-1 bg-transparent border-none outline-none text-green-400 text-xs font-mono placeholder-gray-700 caret-green-400"
                    aria-label="Terminal input"
                    autoFocus
                />
            </div>
        </div>
    );
};

export default TerminalWindow;
