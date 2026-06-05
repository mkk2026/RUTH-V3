import React, { useEffect, useRef } from 'react';

const TopAudioBar = ({ analyserRef }) => {
    const canvasRef = useRef(null);
    const animationFrameRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        // Create a local data array to store frequency data
        const dataArray = new Uint8Array(32); // Default fallback size
        let actualDataArray = null;

        const draw = () => {
            const width = canvas.width;
            const height = canvas.height;
            ctx.clearRect(0, 0, width, height);

            // Get data from the analyser node directly
            if (analyserRef?.current) {
                if (!actualDataArray || actualDataArray.length !== analyserRef.current.frequencyBinCount) {
                     actualDataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
                }
                analyserRef.current.getByteFrequencyData(actualDataArray);
                // Copy over to our fixed size array for visualization
                for (let i = 0; i < Math.min(dataArray.length, actualDataArray.length); i++) {
                    dataArray[i] = actualDataArray[i];
                }
            } else {
                // If no analyser, zero out the array
                dataArray.fill(0);
            }

            const barWidth = 4;
            const gap = 2;
            const totalBars = Math.floor(width / (barWidth + gap));

            // Simple visualization logic
            // Assuming data is an array of 0-255 values
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

            animationFrameRef.current = requestAnimationFrame(draw);
        };

        animationFrameRef.current = requestAnimationFrame(draw);

        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
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
