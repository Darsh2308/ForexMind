// Visual verification for Phase 3 (History view). Assumes the dev server is
// running and the backend has been seeded via
// scripts/seed_demo_recommendations.py (run from the repo root).
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

await page.goto(`${BASE_URL}/history`)
await page.waitForSelector('text=Recommendation history')
// Five real seeded rows across all four statuses - scoped to the row list,
// not the filter <select>, which also has a "PENDING" <option>.
await page.waitForSelector('ul li:has-text("PENDING")')
await shot('05-history-all.png')

await page.selectOption('select[aria-label="Filter by status"]', 'WIN')
await page.waitForTimeout(150)
await shot('06-history-filtered-win.png')

// A filter combination that yields zero rows: WAIT is never persisted by the
// real pipeline, so this must land on the "no recommendations match" state.
await page.selectOption('select[aria-label="Filter by status"]', 'ALL')
await page.selectOption('select[aria-label="Filter by recommendation"]', 'WAIT')
await page.waitForTimeout(150)
await shot('07-history-filtered-empty.png')

console.log('console errors:', consoleErrors.length ? consoleErrors : 'none')
await browser.close()
