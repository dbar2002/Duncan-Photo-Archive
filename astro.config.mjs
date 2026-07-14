import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
  site: 'https://your-domain.example',
  image: {
    // Sharp is the default service; tune quality/formats per-image in components.
    service: { entrypoint: 'astro/assets/services/sharp' },
  },
  build: {
    // Inline small stylesheets, keep large ones as files.
    inlineStylesheets: 'auto',
  },
});
