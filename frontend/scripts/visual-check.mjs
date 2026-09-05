// One-off (but reusable) visual verification driver: launches headless
// Chromium against the already-running dev server, drives one real user
// flow, and saves screenshots + console errors to ./screenshots.
//
// Usage: node scripts/visual-check.mjs <path> <out-dir>
// Assumes the Vite dev server (and, for flows that call it, the backend)
// are already running - see frontend/Development.md for how to start both.

import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const outDir = process.argv[2] ?? 'screenshots'
mkdirSync(outDir, { recursive: true })

const consoleErrors = []

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push(msg.text())
})
page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`))

async function shot(name) {
  await page.screenshot({ path: path.join(outDir, name), fullPage: true })
  console.log(`saved ${name}`)
}

await page.goto(BASE_URL)
await page.waitForSelector('text=Should I buy EUR/USD right now?')
await shot('01-analyze-initial.png')

await page.click('button:has-text("Analyze EUR/USD now")')
// The progress step list should appear almost immediately.
await page.waitForSelector('text=Fetching live market data', { timeout: 5000 })
await shot('02-analyze-loading.png')

// Real backend call: give it a generous window (Groq/Ollama fallback chain
// plus real Twelve Data can take a while). The button relabeling to "Analyze
// again" only happens once the mutation actually settles (success or
// error) - unlike "Reasoning", which is always present as step 5's label.
await page.locator('button:has-text("Analyze again")').waitFor({ timeout: 60000 })
await page.waitForTimeout(300) // let the final paint settle
await shot('03-analyze-result.png')

console.log('console errors:', consoleErrors.length ? consoleErrors : 'none')

await browser.close()
