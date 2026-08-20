import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: process.env.DOCKER_BUILD === "true" ? "standalone" : undefined,
  distDir: process.env.NEXT_BUILD_DIR ?? ".next",
};

export default nextConfig;
