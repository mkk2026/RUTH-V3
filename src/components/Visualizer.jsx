import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

const Visualizer = ({ socket, isListening, width = 600, height = 400 }) => {
    const canvasRef = useRef(null);

    const audioDataRef = useRef(new Array(64).fill(0));
    const intensityRef = useRef(0);
    const isListeningRef = useRef(isListening);

    useEffect(() => {
        isListeningRef.current = isListening;
    }, [isListening]);

    useEffect(() => {
        if (!socket) return;

        const handleAudioData = (data) => {
            if (data && data.data) {
                const aiAudioData = data.data;
                audioDataRef.current = aiAudioData;
                const audioAmp = aiAudioData.reduce((a, b) => a + b, 0) / aiAudioData.length / 255;
                intensityRef.current = audioAmp;
            }
        };

        socket.on('audio_data', handleAudioData);
        return () => {
            socket.off('audio_data', handleAudioData);
        };
    }, [socket]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        // Ensure canvas internal resolution matches display size for sharpness
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        let animationId;

        const draw = () => {
            const w = canvas.width;
            const h = canvas.height;
            const centerX = w / 2;
            const centerY = h / 2;

            // Use current audio data from ref if we were using it for visualization
            // Currently the effect only uses 'intensity', passed as prop. 
            // To ensure we aren't re-triggering this effect constantly, we use refs.

            const currentIntensity = intensityRef.current;
            const currentIsListening = isListeningRef.current;

            const baseRadius = Math.min(w, h) * 0.25;
            const radius = baseRadius + (currentIntensity * 40);

            ctx.clearRect(0, 0, w, h);

            // Base Circle (Glow)
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius - 10, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(245, 158, 11, 0.1)';
            ctx.lineWidth = 2;
            ctx.stroke();

            if (!currentIsListening) {
                // Idle State: Breathing Circle
                const time = Date.now() / 1000;
                const breath = Math.sin(time * 2) * 5;

                ctx.beginPath();
                ctx.arc(centerX, centerY, radius + breath, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(251, 191, 36, 0.5)';
                ctx.lineWidth = 4;
                ctx.shadowBlur = 20;
                ctx.shadowColor = '#22d3ee';
                ctx.stroke();
                ctx.shadowBlur = 0;
            } else {
                // Active State: Just the Circle causing the pulse
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(251, 191, 36, 0.8)';
                ctx.lineWidth = 4;
                ctx.shadowBlur = 20;
                ctx.shadowColor = '#22d3ee';
                ctx.stroke();
                ctx.shadowBlur = 0;
            }

            animationId = requestAnimationFrame(draw);
        };

        draw();
        return () => cancelAnimationFrame(animationId);
    }, [width, height]);

    return (
        <div className="relative" style={{ width, height }}>
            {/* Central Logo/Text */}
            <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
                <motion.div
                    animate={{ scale: isListening ? [1, 1.1, 1] : 1 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                    className="text-amber-100 font-bold tracking-widest drop-shadow-[0_0_15px_rgba(251,191,36,0.8)]"
                    style={{ fontSize: Math.min(width, height) * 0.1 }}
                >
                    R.U.T.H.
                </motion.div>
            </div>

            <canvas
                ref={canvasRef}
                style={{ width: '100%', height: '100%' }}
            />
        </div>
    );
};

export default Visualizer;
