
module.exports = nextConfig;
/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // Ignora ESLint durante a build (não impede que desenvolvas com lint localmente)
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Ignora erros de types na build (o app continua a compilar e correr)
    ignoreBuildErrors: true,
  },
};

module.exports = nextConfig;
