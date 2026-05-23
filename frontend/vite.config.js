import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // base: process.env.VITE_BASE_PATH || "/Blaze",
  optimizeDeps: {
      // exclude: ['@tabler/icons'],
      // include: ['@mui/icons-material'],
    //   esbuildOptions: {
    //   conditions: ['import', 'module', 'browser', 'default'],
    // },
  },

  //   resolve: {
  //   conditions: ['import', 'module', 'browser', 'default'],
  // },
  // resolve: {
  //   alias: {
  //     '@tabler/icons-react': '@tabler/icons-react/dist/esm/icons/index.mjs',
  //   },
  // },

  // resolve: {
  //   conditions: ['browser'],
  //   // alias: {
  //   //   '@mui/icons-material': '@mui/icons-material/index.js',
  //   // },
    
  // }
})
