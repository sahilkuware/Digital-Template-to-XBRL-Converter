/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html.jinja",  // Scan Jinja templates
        "./static/**/*.js",  // Scan JavaScript files
    ],
    theme: {
        extend: {},
    },
    plugins: [],
};
