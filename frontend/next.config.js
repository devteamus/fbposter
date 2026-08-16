/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export → produces /out folder with HTML/CSS/JS
  // Flask serves these files directly. No Node.js runtime needed.
  output: 'export',
  images: {
    unoptimized: true,
  },
  // No rewrites — frontend now talks to same-origin /api/* via Flask
};
module.exports = nextConfig;
