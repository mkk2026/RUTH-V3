/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                mono: ['"JetBrains Mono"', 'monospace'],
            },
            colors: {
                amber: {
                    400: '#fbbf24',
                    500: '#f59e0b',
                    900: '#78350f',
                }
            }
        },
    },
    plugins: [],
}
