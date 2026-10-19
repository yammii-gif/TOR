import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'tests',use:{baseURL:'http://localhost:3000',headless:true,launchOptions:{executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']}},workers:1});
