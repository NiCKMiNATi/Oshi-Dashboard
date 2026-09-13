import { expect, test } from "@playwright/test";
import type { Oshi } from "../lib/types";

const API = "http://127.0.0.1:8000";

for (const [query, name] of [
  ["Higedan", "Official髭男dism"],
  ["ITZY", "ITZY"],
]) {
  test(`discover ${query}, track, remove, discover again, and re-add`, async ({
    page,
    request,
  }) => {
    const ids = new Set<number>();
    const beforeStats = await (await request.get(`${API}/api/stats`)).json();
    const beforeUpdates = await (
      await request.get(`${API}/api/updates`)
    ).json();
    const discovery = page.getByRole("dialog", {
      name: "Discover oshi",
      exact: true,
    });
    async function search() {
      await page.locator(".sidebar-add").click();
      await expect(
        discovery.getByRole("searchbox", { name: "Search oshi" }),
      ).toBeFocused();
      await discovery.getByRole("searchbox").fill(query);
      await expect(
        discovery.getByRole("heading", { name, exact: true }),
      ).toBeVisible();
    }
    async function add() {
      const response = page.waitForResponse(
        (response) =>
          response.url().includes("/api/discover/") &&
          response.request().method() === "POST",
      );
      await discovery
        .getByRole("button", { name: `Add ${name}`, exact: true })
        .click();
      const added = await response;
      expect(added.status()).toBe(201);
      const oshi: Oshi = await added.json();
      ids.add(oshi.id);
      await expect(
        discovery.getByRole("button", {
          name: `Tracking ${name}`,
          exact: true,
        }),
      ).toBeDisabled();
      // The shared sidebar is updated even while the modal remains open.
      await expect(
        page.locator(".oshi-link-name").filter({ hasText: name }),
      ).toHaveCount(1);
      return oshi;
    }
    try {
      await page.goto("/");
      await search();
      const first = await add();
      await page.screenshot({
        path: `test-results/discover-${query.toLowerCase()}.png`,
      });
      await discovery.getByRole("button", { name: "Close discovery" }).click();
      await expect(page.locator(".sidebar-add")).toBeFocused();
      await search();
      await expect(
        discovery.getByRole("button", {
          name: `Tracking ${name}`,
          exact: true,
        }),
      ).toBeDisabled();
        await page.keyboard.press("Escape");
        await expect(discovery).not.toBeVisible();
      await page
        .getByRole("link", { name: "Oshi Management", exact: true })
        .click();
      const row = page.locator(`[data-oshi-id="${first.id}"]`);
      await expect(row).toBeVisible();
      await row
        .getByRole("button", { name: `Remove ${name}`, exact: true })
        .click();
      await page
        .getByRole("dialog", {
          name: `Remove ${name} from My Oshi?`,
          exact: true,
        })
        .getByRole("button", { name: "Remove", exact: true })
        .click();
      await expect(row).toHaveCount(0);
      await expect(
        page.locator(".oshi-link-name").filter({ hasText: name }),
      ).toHaveCount(0);
      await search();
      await add();
      // Management and stats also refresh without navigating or reloading.
      await expect(
        page.locator(".table-oshi-name").filter({ hasText: name }),
      ).toHaveCount(1);
      await expect(page.locator(".stat-card strong").first()).toHaveText(
        String(beforeStats.active_oshi + 1),
      );
      expect(await (await request.get(`${API}/api/updates`)).json()).toEqual(
        beforeUpdates,
      );
    } finally {
      for (const id of ids) await request.delete(`${API}/api/oshi/${id}`);
    }
  });
}

test("no results offers manual creation with aliases, independent of catalog", async ({
  page,
  request,
}) => {
  const name = "My obscure discovery test favorite";
  let id: number | undefined;
  try {
    await page.goto("/oshi");
    await page
      .locator(".page-header")
      .getByRole("button", { name: "+ Add oshi", exact: true })
      .click();
    const discovery = page.getByRole("dialog", { name: "Discover oshi" });
    await discovery.getByRole("searchbox").fill(name);
    await expect(
      discovery.getByText(`No matches for “${name}” in this collection.`),
    ).toBeVisible();
    await discovery
      .getByRole("button", { name: "+ Add manually", exact: true })
      .click();
    const form = page.getByRole("dialog", { name: "Add an oshi", exact: true });
    await expect(form.getByLabel("Name", { exact: true })).toHaveValue(name);
    await expect(form.getByLabel("Name", { exact: true })).toBeFocused();
    await expect(form.getByLabel("Priority", { exact: true })).toHaveCount(0);
    await form.getByLabel("Type", { exact: true }).selectOption("OTHER");
    await form
      .getByRole("button", { name: "+ Add keyword", exact: true })
      .click();
    await form
      .getByRole("textbox", { name: "Keyword 1", exact: true })
      .fill("A personal nickname");
    await page.screenshot({ path: "test-results/discover-manual.png" });
    const created = page.waitForResponse(
      (response) =>
        response.url() === `${API}/api/oshi` &&
        response.request().method() === "POST",
    );
    await form.getByRole("button", { name: "Add oshi", exact: true }).click();
    const oshi: Oshi = await (await created).json();
    id = oshi.id;
    await expect(form).not.toBeVisible();
    await expect(page.locator(`[data-oshi-id="${id}"]`)).toBeVisible();
    await expect(
      page.locator(".oshi-link-name").filter({ hasText: name }),
    ).toHaveCount(1);
    expect(oshi.priority).toBe(50);
    expect(
      oshi.keywords.map(({ value, weight }) => ({ value, weight })),
    ).toEqual([{ value: "A personal nickname", weight: 1 }]);
    expect(
      await (
        await request.get(`${API}/api/discover`, { params: { q: name } })
      ).json(),
    ).toEqual([]);
  } finally {
    if (id !== undefined) await request.delete(`${API}/api/oshi/${id}`);
  }
});

test("discovery debounces, discards obsolete results, and recovers from search and add errors", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  let release = () => {};
  let id: number | undefined;
  try {
    await page.goto("/");
    await page.locator(".sidebar-add").click();
    const dialog = page.getByRole("dialog", { name: "Discover oshi" });
    const input = dialog.getByRole("searchbox");
    const searches: string[] = [];
    page.on("request", (request) => {
      if (request.url().startsWith(`${API}/api/discover?`))
        searches.push(request.url());
    });
    await page.route(`${API}/api/discover?*`, (route) =>
      route.abort("connectionrefused"),
    );
    await input.pressSequentially("Higedan", { delay: 15 });
    await expect(dialog.getByRole("alert")).toContainText(
      "local API is unavailable",
    );
    expect(searches).toHaveLength(1);
    await page.unroute(`${API}/api/discover?*`);
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    let requested = () => {};
    const received = new Promise<void>((resolve) => {
      requested = resolve;
    });
    await page.route(`${API}/api/discover?q=Higedan`, async (route) => {
      const response = await route.fetch();
      requested();
      await held;
      await route.fulfill({ response });
    });
    await dialog.getByRole("button", { name: "Try again" }).click();
    await received;
    await expect(dialog.getByText("Searching…", { exact: true })).toBeVisible();
    await input.fill("Gojo");
    await expect(
      dialog.getByRole("heading", { name: "五条悟", exact: true }),
    ).toBeVisible();
    release();
    await page.unrouteAll({ behavior: "wait" });
    await expect(
      dialog.getByRole("heading", { name: "Official髭男dism", exact: true }),
    ).toHaveCount(0);
    await page.route(`${API}/api/discover/*/track`, (route) =>
      route.fulfill({
        status: 503,
        json: { detail: "Please try adding again" },
      }),
    );
    await dialog
      .getByRole("button", { name: "Add 五条悟", exact: true })
      .click();
    await expect(dialog.getByRole("alert")).toHaveText(
      "Please try adding again",
    );
    await expect(
      dialog.getByRole("button", { name: "Add 五条悟", exact: true }),
    ).toBeEnabled();
    await expect(
      page.locator(".oshi-link-name").filter({ hasText: "五条悟" }),
    ).toHaveCount(0);
    await page.unrouteAll();
    const response = page.waitForResponse((response) =>
      response.url().endsWith("/track"),
    );
    await dialog
      .getByRole("button", { name: "Add 五条悟", exact: true })
      .click();
    id = (await (await response).json()).id;
    await expect(
      dialog.getByRole("button", { name: "Tracking 五条悟", exact: true }),
    ).toBeDisabled();
    expect(errors).toEqual([]);
  } finally {
    release();
    if (!page.isClosed()) await page.unrouteAll({ behavior: "ignoreErrors" });
    if (id !== undefined) await request.delete(`${API}/api/oshi/${id}`);
  }
});
