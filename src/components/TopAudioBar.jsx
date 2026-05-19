import React, { useEffect, useRef } from 'react';

const TopAudioBar = ({ analyserRef }) => {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let animationFrameId;

        // Instantiate the array once outside the animation loop
        let audioDataArray = new Uint8Array(32); // Default fallback size

        // Let's assume an initial setup, but we update the size dynamically if it changes
        let lastBinCount = 0;

        const draw = () => {
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

            // Get data directly from analyser
            let validData = false;
            if (analyserRef?.current) {
                const binCount = analyserRef.current.frequencyBinCount;
                if (binCount !== lastBinCount) {
                    audioDataArray = new Uint8Array(binCount);
                    lastBinCount = binCount;
                }
                analyserRef.current.getByteFrequencyData(audioDataArray);
                validData = true;
            }

            for (let i = 0; i < totalBars / 2; i++) {
                const value = validData ? (audioDataArray[i % audioDataArray.length] || 0) : 0;
                const percent = value / 255;
                const barHeight = Math.max(2, percent * height);

                ctx.fillStyle = `rgba(251, 191, 36, ${0.2 + percent * 0.8})`; // Cyan with opacity

                // Right side
                ctx.fillRect(center + i * (barWidth + gap), (height - barHeight) / 2, barWidth, barHeight);

                // Left side
                ctx.fillRect(center - (i + 1) * (barWidth + gap), (height - barHeight) / 2, barWidth, barHeight);
            }
            animationFrameId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
            }
        };
    }, [analyserRef]);

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
