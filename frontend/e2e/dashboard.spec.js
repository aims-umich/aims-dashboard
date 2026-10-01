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

const isMobile = (testInfo) => testInfo.project.name === "mobile"

test("overview introduces the project and shows every live source", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { level: 1, name: "Nuclear Sentiment Analysis" })).toBeVisible()
  await expect(page.getByRole("link", { name: /Read the paper/ }).first()).toHaveAttribute("href", /sciencedirect\.com/)
  for (const title of ["Where each source stands", "Last 24 hours", "Last 30 days"]) {
    await expect(page.getByRole("heading", { level: 2, name: title })).toBeVisible()
  }
  const cards = page.locator("#src-h").locator("xpath=ancestor::section[1]")
  for (const { name, route } of PLATFORMS) {
    await expect(cards.locator(`a[href="${route}"]`)).toContainText(name)
  }
  await expect(cards.locator('a[href="/reddit"]')).toHaveCount(0)
})

test("the range on the overview changes the data shown", async ({ page }) => {
  await page.goto("/")
  const scale = page.locator("#scale-h").locator("xpath=ancestor::section[1]")
  await scale.getByRole("radio", { name: "30 days" }).click()
  await expect(scale.getByRole("radio", { name: "30 days" })).toHaveAttribute("aria-checked", "true")
})

for (const { route, name } of PLATFORMS) {
  test(`${name} page renders its charts, words, and recent items`, async ({ page }) => {
    await page.goto(route)
    await expect(page).toHaveTitle(new RegExp(name))
    await expect(page.getByRole("heading", { level: 1, name })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Sentiment over time" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Sentiment split" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Model confidence" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Top words by sentiment" })).toBeVisible()
    const posts = page.locator("#posts-h").locator("xpath=ancestor::section[1]").locator("article")
    await expect(posts.first()).toBeVisible()
    expect(await posts.count()).toBeGreaterThan(5)
  })
}

test("range selection is reflected in the URL and survives reload", async ({ page }) => {
  await page.goto("/mastodon")
  await page.getByRole("radiogroup", { name: "Time range" }).getByRole("radio", { name: "90 days" }).click()
  await expect(page).toHaveURL(/range=90d/)
  await page.reload()
  await expect(page.getByRole("radiogroup", { name: "Time range" }).getByRole("radio", { name: "90 days" })).toHaveAttribute(
    "aria-checked",
    "true",
  )
})

test("filtering recent posts by sentiment shows only that label", async ({ page }) => {
  await page.goto("/bluesky")
  const section = page.locator("#posts-h").locator("xpath=ancestor::section[1]")
  await section.getByRole("radiogroup", { name: "Filter by sentiment" }).getByRole("radio", { name: "Negative" }).click()
  const posts = section.locator("article")
  await expect(posts.first()).toBeVisible()
  const labels = await posts.locator("span.font-semibold:has(> span.rounded-full)").allInnerTexts()
  expect(labels.length).toBeGreaterThan(0)
  for (const label of labels) expect(label.trim()).toBe("Negative")
})

test("articles list the sentences they were scored on", async ({ page }) => {
  await page.goto("/guardian")
  const section = page.locator("#posts-h").locator("xpath=ancestor::section[1]")
  const sentences = section.locator("article li")
  await expect(sentences.first()).toBeVisible()
  // Pin the card by position: once expanded it no longer matches a "Show more" filter.
  const index = await section
    .locator("article")
    .evaluateAll((cards) => cards.findIndex((c) => /Show \d+ more/.test(c.textContent)))
  expect(index).toBeGreaterThanOrEqual(0)
  const card = section.locator("article").nth(index)
  const shown = await card.locator("li").count()
  await card.getByRole("button", { name: /^Show \d+ more/ }).click()
  await expect(card.getByRole("button", { name: "Show fewer sentences" })).toHaveAttribute("aria-expanded", "true")
  expect(await card.locator("li").count()).toBeGreaterThan(shown)
})

test("compare, topics, events and model pages render", async ({ page }) => {
  await page.goto("/compare")
  await expect(page.getByRole("heading", { level: 1, name: "Compare sources" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Social platforms and newspapers" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Correlation between sources" })).toBeVisible()

  await page.goto("/topics")
  await expect(page.getByRole("heading", { level: 1, name: "Topics" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Topic landscape" })).toBeVisible()
  await page.getByRole("button", { name: /^Fusion/ }).last().click()
  await expect(page.getByRole("heading", { level: 2, name: "Fusion" })).toBeVisible()

  await page.goto("/events")
  await expect(page.getByRole("heading", { level: 1, name: "Events" })).toBeVisible()
  await expect(page.getByText("Fusion ignition at the National Ignition Facility").first()).toBeVisible()
  await expect(page.getByRole("heading", { name: "Detected spikes" })).toBeVisible()

  await page.goto("/model")
  await expect(page.getByRole("heading", { level: 1, name: "Model" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Where the model hesitates" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Known failure modes" })).toBeVisible()
})

test("the theme toggle switches themes and is remembered", async ({ page }, testInfo) => {
  await page.goto("/about")
  const html = page.locator("html")
  const before = await html.getAttribute("data-theme")
  if (isMobile(testInfo)) await page.getByRole("button", { name: "More" }).click()
  await page.getByRole("button", { name: /Switch to (light|dark) theme/ }).click()
  const after = before === "dark" ? "light" : "dark"
  await expect(html).toHaveAttribute("data-theme", after)
  await page.reload()
  await expect(html).toHaveAttribute("data-theme", after)
})

test("phones navigate with the tab bar and the More sheet", async ({ page }, testInfo) => {
  test.skip(!isMobile(testInfo), "phone layout only")
  await page.goto("/")
  const tabs = page.getByRole("navigation", { name: "Main" })
  await tabs.getByRole("link", { name: "Compare" }).click()
  await expect(page).toHaveURL(/\/compare$/)
  await tabs.getByRole("button", { name: "More" }).click()
  await page.getByRole("dialog", { name: "More pages" }).getByRole("link", { name: "Events" }).click()
  await expect(page).toHaveURL(/\/events$/)
  await expect(page.getByRole("dialog", { name: "More pages" })).toHaveCount(0)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(0)
})

test("about page and unknown routes", async ({ page }) => {
  await page.goto("/about")
  await expect(page.getByRole("heading", { level: 1, name: "How it works" })).toBeVisible()
  await page.goto("/threads")
  await expect(page.getByRole("heading", { name: "This page does not exist" })).toBeVisible()
  await page.goto("/times")
  await expect(page).toHaveURL(/\/nyt$/)
})
