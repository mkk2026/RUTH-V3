import React, { useEffect, useRef } from 'react';

const TopAudioBar = ({ analyser }) => {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        let animationId;
        const dataArray = analyser ? new Uint8Array(analyser.frequencyBinCount) : new Uint8Array(32).fill(0);

        const draw = () => {
            if (analyser) {
                analyser.getByteFrequencyData(dataArray);
            }

            const width = canvas.width;
            const height = canvas.height;
            ctx.clearRect(0, 0, width, height);

            const barWidth = 4;
            const gap = 2;
            const totalBars = Math.floor(width / (barWidth + gap));

            // Simple visualization logic
            // Assuming audioData is an array of 0-255 values
            // We mirror it from center

            const center = width / 2;

            for (let i = 0; i < totalBars / 2; i++) {
                const value = dataArray[i % dataArray.length] || 0;
                const percent = value / 255;
                const barHeight = Math.max(2, percent * height);

                ctx.fillStyle = `rgba(251, 191, 36, ${0.2 + percent * 0.8})`; // Cyan with opacity

                // Right side
                ctx.fillRect(center + i * (barWidth + gap), (height - barHeight) / 2, barWidth, barHeight);

                // Left side
                ctx.fillRect(center - (i + 1) * (barWidth + gap), (height - barHeight) / 2, barWidth, barHeight);
            }

            animationId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            if (animationId) cancelAnimationFrame(animationId);
        };
    }, [analyser]);

    return (
        <canvas
            ref={canvasRef}
            width={300}
            height={40}
            className="opacity-80"
        />
    );
};

export default TopAudioBar;
