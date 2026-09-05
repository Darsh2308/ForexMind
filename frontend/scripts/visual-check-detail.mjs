// Visual verification for Phase 4 (evidence drill-down). Assumes the dev
// server + backend are running and a full-context recommendation has been
// seeded via scripts/seed_demo_recommendation_with_context.py (repo root).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const RECOMMENDATION_ID = process.argv[3] ?? '6'
const outDir = process.argv[2] ?? 'screenshots'
mkdirSync(outDir, { recursive: true })

const consoleErrors = []
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 1400 } })
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push(msg.text())
})
page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`))

async function shot(name) {
  await page.screenshot({ path: path.join(outDir, name), fullPage: true })
  console.log(`saved ${name}`)
}

await page.goto(`${BASE_URL}/history/${RECOMMENDATION_ID}`)
await page.waitForSelector('text=Technical Analysis', { timeout: 15000 })
await shot('09-detail-collapsed.png')

// Expand every section panel to prove they all actually render real data,
// not just that the collapsed headers exist.
const summaries = await page.locator('details > summary').all()
for (const summary of summaries) {
  await summary.click()
}
await page.waitForTimeout(200)
await shot('10-detail-expanded-top.png')

// The page is long once everything is open - scroll partway to capture the
// deeper agent sections too (SMC, Elliott Wave/Wyckoff advisory badges, news).
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.45))
await shot('11-detail-expanded-mid.png')

console.log('console errors:', consoleErrors.length ? consoleErrors : 'none')
await browser.close()
