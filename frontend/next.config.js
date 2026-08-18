/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 'standalone' produces a minimal self-contained server bundle
  // (.next/standalone) instead of requiring the full node_modules folder
  // copied into the runtime image — smaller, faster-starting containers.
  // NOTE: if you switch to this, frontend/Dockerfile's final stage needs to
  // COPY .next/standalone + .next/static instead of node_modules — left as
  // 'export default' style comment here rather than silently changing the
  // Dockerfile, since that's a coordinated two-file change.
  // output: 'standalone',
};

module.exports = nextConfig;
