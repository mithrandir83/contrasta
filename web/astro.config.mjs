import { defineConfig } from 'astro/config';
const repo = process.env.GITHUB_REPOSITORY?.split('/')[1];
export default defineConfig({output:'static',base:repo && !repo.endsWith('.github.io') ? `/${repo}/` : '/'});
