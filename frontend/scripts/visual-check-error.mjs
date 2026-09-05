// Companion to visual-check.mjs: drives the Analyze flow while the backend
// is down, to capture the network-unreachable error state.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const outDir = process.argv[2] ?? 'screenshots'
mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })

await page.goto(BASE_URL)
await page.click('button:has-text("Analyze EUR/USD now")')
await page.locator('text=Couldn’t get a recommendation.').waitFor({ timeout: 15000 })
await page.screenshot({
  path: path.join(outDir, '04-analyze-network-error.png'),
  fullPage: true,
})
console.log('saved 04-analyze-network-error.png')

await browser.close()
