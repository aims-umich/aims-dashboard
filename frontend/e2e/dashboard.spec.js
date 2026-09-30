import { expect, test as base } from "@playwright/test"

// Every test fails if the page throws or logs a console error.
const test = base.extend({
  page: async ({ page }, use) => {
    const problems = []
    page.on("pageerror", (error) => problems.push(error.message))
    page.on("console", (message) => message.type() === "error" && problems.push(message.text()))
    await use(page)
    expect(problems, "console errors").toEqual([])
  },
})

const PLATFORMS = [
  { route: "/bluesky", name: "Bluesky" },
  { route: "/mastodon", name: "Mastodon" },
  { route: "/youtube", name: "YouTube" },
  { route: "/guardian", name: "The Guardian" },
  { route: "/nyt", name: "New York Times" },
]

test("home lists every live platform with fresh data", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Public sentiment toward nuclear energy, live" })).toBeVisible()
  const main = page.getByRole("main")
  for (const { name } of PLATFORMS) {
    await expect(main.getByRole("link", { name: new RegExp(name) })).toBeVisible()
  }
  await expect(main.getByText(/Live · updated/)).toHaveCount(PLATFORMS.length)
  await expect(main.getByRole("link", { name: /Reddit/ })).toHaveCount(0)
})

for (const { route, name } of PLATFORMS) {
  test(`${name} dashboard renders charts, words, and recent items`, async ({ page }) => {
    await page.goto(route)
    await expect(page).toHaveTitle(new RegExp(name))
    await expect(page.getByText(/Live · updated/).first()).toBeVisible()
    await expect(page.getByText("Sentiment over time")).toBeVisible()
    await expect(page.locator("svg.recharts-surface").first()).toBeVisible()
    await expect(page.getByText("Top words by sentiment")).toBeVisible()
    const items = page.locator("main ul > li")
    await expect(items.first()).toBeVisible()
    expect(await items.count()).toBeGreaterThan(5)
  })
}

test("range selection is reflected in the URL and survives reload", async ({ page }) => {
  await page.goto("/mastodon")
  await page.getByRole("radio", { name: "90 days" }).click()
  await expect(page).toHaveURL(/range=90d/)
  await expect(page.getByText("Share of scored posts per week", { exact: false })).toBeVisible()
  await page.reload()
  await expect(page.getByRole("radio", { name: "90 days" })).toHaveAttribute("aria-checked", "true")
})

test("filtering recent posts by sentiment shows only that label", async ({ page }) => {
  await page.goto("/bluesky")
  const list = page.locator("main section").filter({ hasText: "Recent posts" })
  await list.getByRole("radio", { name: "Negative" }).click()
  await expect(list.locator("li").first()).toBeVisible()
  const labels = await list.locator("li span.rounded-full").allInnerTexts()
  expect(labels.length).toBeGreaterThan(0)
  for (const label of labels) expect(label).toMatch(/^Negative/)
})

test("about page and unknown routes", async ({ page }) => {
  await page.goto("/about")
  await expect(page.getByRole("heading", { name: "How the dashboard works" })).toBeVisible()
  await page.goto("/threads")
  await expect(page.getByRole("heading", { name: "This page does not exist" })).toBeVisible()
  await page.goto("/times")
  await expect(page).toHaveURL(/\/nyt$/)
})
