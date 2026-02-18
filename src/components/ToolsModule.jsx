import React, { useState } from 'react';
import {
    Mic, MicOff, Settings, Power, Video, VideoOff, Hand, Lightbulb, Printer, Globe, Box,
    Terminal, CalendarClock, Bell, Plug, MessageSquare, Puzzle, Cpu, Brain,
    ChevronUp, ChevronDown
} from 'lucide-react';

const ToolsModule = ({
    isConnected,
    isMuted,
    isVideoOn,
    isHandTrackingEnabled,
    showSettings,
    onTogglePower,
    onToggleMute,
    onToggleVideo,
    onToggleSettings,
    onToggleHand,
    onToggleKasa,
    showKasaWindow,
    onTogglePrinter,
    showPrinterWindow,
    onToggleCad,
    showCadWindow,
    onToggleBrowser,
    showBrowserWindow,
    onToggleTerminal,
    showTerminal,
    onToggleScheduler,
    showScheduler,
    onToggleAlerts,
    showAlerts,
    onToggleIntegrations,
    showIntegrations,
    onToggleMessaging,
    showMessaging,
    onTogglePlugins,
    showPlugins,
    onToggleModelSettings,
    showModelSettings,
    onToggleMemoryViewer,
    showMemoryViewer,
    activeDragElement,
    position,
    onMouseDown
}) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const handleToggleExpand = () => {
        setIsExpanded(prev => !prev);
    };

    return (
        <div
            id="tools"
            onMouseDown={onMouseDown}
            className="absolute flex flex-col items-center gap-2 transition-all duration-200"
            style={{
                left: position.x,
                top: position.y,
                transform: 'translate(-50%, -50%)',
                pointerEvents: 'auto'
            }}
        >
            {/* Secondary Row (expandable) */}
            {isExpanded && (
                <div className="px-4 py-2 backdrop-blur-xl bg-black/40 border border-white/10 shadow-2xl rounded-full animate-in fade-in slide-in-from-bottom-2 duration-200">
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay rounded-full"></div>
                    <div className="flex justify-center gap-4 relative z-10">
                        {/* Terminal */}
                        <button
                            onClick={onToggleTerminal}
                            className={`p-2.5 rounded-full border-2 transition-all duration-300 ${showTerminal
                                ? 'border-emerald-400 bg-emerald-400/10 text-emerald-400 hover:bg-emerald-400/20 shadow-[0_0_15px_rgba(52,211,153,0.3)]'
                                : 'border-amber-900 text-amber-700 hover:border-emerald-500 hover:text-emerald-500'
                                }`}
                            aria-label="Toggle Terminal"
                            tabIndex={0}
                        >
                            <Terminal size={20} />
                        </button>

                        {/* Scheduler */}
                        <button
                            onClick={onToggleScheduler}
                            className={`p-2.5 rounded-full border-2 transition-all duration-300 ${showScheduler
                                ? 'border-amber-400 bg-amber-400/10 text-amber-400 hover:bg-amber-400/20 shadow-[0_0_15px_rgba(251,191,36,0.3)]'
                                : 'border-amber-900 text-amber-700 hover:border-amber-500 hover:text-amber-500'
                                }`}
                            aria-label="Toggle Scheduler"
                            tabIndex={0}
                        >
                            <CalendarClock size={20} />
                        </button>

                        {/* Alerts */}
                        <button
                            onClick={onToggleAlerts}
                            className={`p-2.5 rounded-full border-2 transition-all duration-300 ${showAlerts
                                ? 'border-rose-400 bg-rose-400/10 text-rose-400 hover:bg-rose-400/20 shadow-[0_0_15px_rgba(251,113,133,0.3)]'
                                : 'border-amber-900 text-amber-700 hover:border-rose-500 hover:text-rose-500'
                                }`}
                            aria-label="Toggle Alerts"
                            tabIndex={0}
                        >
                            <Bell size={20} />
                        </button>

                        {/* Integrations */}
                        <button
                            onClick={onToggleIntegrations}
                            className={`p-2.5 rounded-full border-2 transition-all duration-300 ${showIntegrations
                                ? 'border-indigo-400 bg-indigo-400/10 text-indigo-400 hover:bg-indigo-400/20 shadow-[0_0_15px_rgba(129,140,248,0.3)]'
                                : 'border-amber-900 text-amber-700 hover:border-indigo-500 hover:text-indigo-500'
                                }`}
                            aria-label="Toggle Integrations"
                            tabIndex={0}
                        >
                            <Plug size={20} />
                        </button>

                        {/* Messaging */}
                        <button
                            onClick={onToggleMessaging}
                            className={`p-2.5 rounded-full border-2 transition-all duration-300 ${showMessaging
                                ? 'border-violet-400 bg-violet-400/10 text-violet-400 hover:bg-violet-400/20 shadow-[0_0_15px_rgba(167,139,250,0.3)]'
                                : 'border-amber-900 text-amber-700 hover:border-violet-500 hover:text-violet-500'
                                }`}
                            aria-label="Toggle Messaging"
                            tabIndex={0}
                        >
                            <MessageSquare size={20} />
                        </button>

                        {/* Plugins */}
                        <button
                            onClick={onTogglePlugins}
                            className={`p-2.5 rounded-full border-2 transition-all duration-300 ${showPlugins
                                ? 'border-teal-400 bg-teal-400/10 text-teal-400 hover:bg-teal-400/20 shadow-[0_0_15px_rgba(45,212,191,0.3)]'
                                : 'border-amber-900 text-amber-700 hover:border-teal-500 hover:text-teal-500'
                                }`}
                            aria-label="Toggle Plugins"
                            tabIndex={0}
                        >
                            <Puzzle size={20} />
                        </button>

                        {/* Model Settings */}
                        <button
                            onClick={onToggleModelSettings}
                            className={`p-2.5 rounded-full border-2 transition-all duration-300 ${showModelSettings
                                ? 'border-sky-400 bg-sky-400/10 text-sky-400 hover:bg-sky-400/20 shadow-[0_0_15px_rgba(56,189,248,0.3)]'
                                : 'border-amber-900 text-amber-700 hover:border-sky-500 hover:text-sky-500'
                                }`}
                            aria-label="Toggle Model Settings"
                            tabIndex={0}
                        >
                            <Cpu size={20} />
                        </button>

                        {/* Memory Viewer */}
                        <button
                            onClick={onToggleMemoryViewer}
                            className={`p-2.5 rounded-full border-2 transition-all duration-300 ${showMemoryViewer
                                ? 'border-pink-400 bg-pink-400/10 text-pink-400 hover:bg-pink-400/20 shadow-[0_0_15px_rgba(244,114,182,0.3)]'
                                : 'border-amber-900 text-amber-700 hover:border-pink-500 hover:text-pink-500'
                                }`}
                            aria-label="Toggle Memory Viewer"
                            tabIndex={0}
                        >
                            <Brain size={20} />
                        </button>
                    </div>
                </div>
            )}

            {/* Primary Row */}
            <div className="px-6 py-3 backdrop-blur-xl bg-black/40 border border-white/10 shadow-2xl rounded-full">
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay rounded-full"></div>

                <div className="flex justify-center gap-6 relative z-10">
                    {/* Power Button */}
                    <button
                        onClick={onTogglePower}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${isConnected
                            ? 'border-green-500 bg-green-500/10 text-green-500 hover:bg-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                            : 'border-gray-600 bg-gray-600/10 text-gray-500 hover:bg-gray-600/20'
                            }`}
                    >
                        <Power size={24} />
                    </button>

                    {/* Mute Button */}
                    <button
                        onClick={onToggleMute}
                        disabled={!isConnected}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${!isConnected
                            ? 'border-gray-800 text-gray-800 cursor-not-allowed'
                            : isMuted
                                ? 'border-red-500 bg-red-500/10 text-red-500 hover:bg-red-500/20 shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                                : 'border-amber-500 bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.3)]'
                            }`}
                    >
                        {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
                    </button>

                    {/* Video Button */}
                    <button
                        onClick={onToggleVideo}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${isVideoOn
                            ? 'border-purple-500 bg-purple-500/10 text-purple-500 hover:bg-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                            : 'border-amber-900 text-amber-700 hover:border-amber-500 hover:text-amber-500'
                            }`}
                    >
                        {isVideoOn ? <Video size={24} /> : <VideoOff size={24} />}
                    </button>

                    {/* Settings Button */}
                    <button
                        onClick={onToggleSettings}
                        className={`p-3 rounded-full border-2 transition-all ${showSettings ? 'border-amber-400 text-amber-400 bg-amber-900/20' : 'border-amber-900 text-amber-700 hover:border-amber-500 hover:text-amber-500'
                            }`}
                    >
                        <Settings size={24} />
                    </button>

                    {/* Hand Tracking Toggle */}
                    <button
                        onClick={onToggleHand}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${isHandTrackingEnabled
                            ? 'border-orange-500 bg-orange-500/10 text-orange-500 hover:bg-orange-500/20 shadow-[0_0_15px_rgba(249,115,22,0.3)]'
                            : 'border-amber-900 text-amber-700 hover:border-amber-500 hover:text-amber-500'
                            }`}
                    >
                        <Hand size={24} />
                    </button>

                    {/* Kasa Light Control */}
                    <button
                        onClick={onToggleKasa}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${showKasaWindow
                            ? 'border-yellow-300 bg-yellow-300/10 text-yellow-300 hover:bg-yellow-300/20 shadow-[0_0_15px_rgba(253,224,71,0.3)]'
                            : 'border-amber-900 text-amber-700 hover:border-amber-500 hover:text-amber-500'
                            }`}
                    >
                        <Lightbulb size={24} />
                    </button>

                    {/* 3D Printer Control */}
                    <button
                        onClick={onTogglePrinter}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${showPrinterWindow
                            ? 'border-green-400 bg-green-400/10 text-green-400 hover:bg-green-400/20'
                            : 'border-amber-900 text-amber-700 hover:border-green-500 hover:text-green-500'
                            }`}
                    >
                        <Printer size={24} />
                    </button>

                    {/* CAD Agent Toggle */}
                    <button
                        onClick={onToggleCad}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${showCadWindow
                            ? 'border-amber-400 bg-amber-400/10 text-amber-400 hover:bg-amber-400/20 shadow-[0_0_15px_rgba(251,191,36,0.3)]'
                            : 'border-amber-900 text-amber-700 hover:border-amber-500 hover:text-amber-500'
                            }`}
                    >
                        <Box size={24} />
                    </button>

                    {/* Web Agent Toggle */}
                    <button
                        onClick={onToggleBrowser}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${showBrowserWindow
                            ? 'border-blue-400 bg-blue-400/10 text-blue-400 hover:bg-blue-400/20 shadow-[0_0_15px_rgba(96,165,250,0.3)]'
                            : 'border-amber-900 text-amber-700 hover:border-blue-500 hover:text-blue-500'
                            }`}
                    >
                        <Globe size={24} />
                    </button>

                    {/* Expand/Collapse Extensions */}
                    <button
                        onClick={handleToggleExpand}
                        className={`p-3 rounded-full border-2 transition-all duration-300 ${isExpanded
                            ? 'border-white/40 bg-white/10 text-white hover:bg-white/20'
                            : 'border-amber-900 text-amber-700 hover:border-amber-500 hover:text-amber-500'
                            }`}
                        aria-label={isExpanded ? 'Collapse extensions toolbar' : 'Expand extensions toolbar'}
                        tabIndex={0}
                    >
                        {isExpanded ? <ChevronDown size={24} /> : <ChevronUp size={24} />}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ToolsModule;
