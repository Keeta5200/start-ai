/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    typedRoutes: false
  },
  generateBuildId: async () => {
    return `build-${Date.now()}`;
  }
};

export default nextConfig;
