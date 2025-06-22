import { withPayload } from '@payloadcms/next/withPayload'

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Your Next.js config here
  output: 'standalone',
  experimental: {
    outputFileTracingIncludes: {
      '/api/**/*': ['./node_modules/.pnpm/@libsql+client@*/**/*'],
      '/app/**/*': ['./node_modules/.pnpm/@libsql+client@*/**/*'],
    },
  },
}

export default withPayload(nextConfig, { devBundleServerPackages: false })
