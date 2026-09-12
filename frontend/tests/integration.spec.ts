import { expect, test } from "@playwright/test";
import type { Oshi, Update } from "../lib/types";

const API = "http://127.0.0.1:8000";

test("seeded feed, real filters, client search, and refresh", async ({
  page,
  request,
}) => {
  const updates: Update[] = await (
    await request.get(`${API}/api/updates`)
  ).json();
  const oshi: Oshi[] = await (await request.get(`${API}/api/oshi`)).json();
  const genshin = oshi.find((item) => item.name === "原神")!;
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().startsWith(API)) requests.push(request.url());
  });
  await page.goto("/");
  await expect(page.locator(".update-card")).toHaveCount(10);
  await expect(page.locator(".new-count")).toHaveText("3 new");
  const scores = await page.locator(".priority-score strong").allTextContents();
  expect(scores.map(Number)).toEqual(
    updates.map((item) => item.relevance_score),
  );
  await page
    .getByRole("navigation", { name: "My oshi" })
    .getByRole("link", { name: "原神", exact: true })
    .click();
  await expect(page.locator(".update-card")).toHaveCount(3);
  await expect(page).toHaveURL(new RegExp(`oshi=${genshin.id}`));
  await page
    .getByRole("group", { name: "Filter by category" })
    .getByRole("button", { name: "Merch", exact: true })
    .click();
  await expect(page.locator(".update-card")).toHaveCount(1);
  await expect(page.locator(".category-badge")).toHaveText("MERCH");
  expect(
    requests.some(
      (url) =>
        url.includes(`oshi=${genshin.id}`) && url.includes("category=MERCH"),
    ),
  ).toBeTruthy();
  await page.getByLabel("Status", { exact: true }).selectOption("SAVED");
  await expect(page.getByText("Nothing here just yet")).toBeVisible();
  await page.getByLabel("Status", { exact: true }).selectOption("BOUGHT");
  await expect(page.locator(".update-card")).toHaveCount(1);
  await page.getByLabel("Minimum score").selectOption("100");
  await expect(page.getByText("Nothing here just yet")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters & search" }).click();
  await expect(page.locator(".update-card")).toHaveCount(10);
  const beforeSearch = requests.length;
  await page
    .getByRole("searchbox", { name: "Search loaded updates" })
    .fill("RYUJIN");
  await expect(page.locator(".update-card")).toHaveCount(3);
  expect(requests.length).toBe(beforeSearch);
  await page.getByRole("searchbox").fill("no such update xyz");
  await expect(
    page.getByText("No matches in your loaded updates"),
  ).toBeVisible();
  await page.getByRole("searchbox").fill("");
  const response = page.waitForResponse((response) =>
    response.url().startsWith(`${API}/api/updates?`),
  );
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await response;
  await expect(page.locator(".update-card")).toHaveCount(10);
  await page.screenshot({ path: "test-results/dashboard.png", fullPage: true });
});

test("detail drawer, keyboard focus, and durable status mutations", async ({
  page,
  request,
}) => {
  const original: Update = await (
    await request.get(`${API}/api/updates/1`)
  ).json();
  await page.goto("/");
  const card = page.locator('[data-update-id="1"]');
  await card.getByRole("button", { name: original.title, exact: true }).click();
  const drawer = page.getByRole("dialog", { name: "Update details" });
  await expect(drawer).toBeVisible();
  await expect(
    drawer.getByRole("heading", { name: original.title }),
  ).toBeVisible();
  await expect(drawer.getByText("Deadline", { exact: true })).toBeVisible();
  await expect(
    drawer.getByText(original.location!, { exact: true }),
  ).toBeVisible();
  await expect(
    drawer.getByRole("link", { name: /Open source/ }),
  ).toHaveAttribute("href", original.source_url);
  await page.screenshot({ path: "test-results/drawer.png" });
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(
    card.getByRole("button", { name: original.title, exact: true }),
  ).toBeFocused();
  try {
    await card.getByRole("button", { name: "Save", exact: true }).click();
    await expect(
      card.getByRole("button", { name: "Saved", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    await page.reload();
    await expect(
      card.getByRole("button", { name: "Saved", exact: true }),
    ).toBeVisible();
    expect(
      (await (await request.get(`${API}/api/updates/1`)).json()).status,
    ).toBe("SAVED");
    await card
      .getByRole("button", { name: original.title, exact: true })
      .click();
    await drawer.getByRole("button", { name: "Going", exact: true }).click();
    await expect(
      drawer.getByRole("button", { name: "Going", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    await drawer.getByRole("button", { name: "Ignore", exact: true }).click();
    await expect(
      drawer.getByRole("button", { name: "Ignored", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(
      (await (await request.get(`${API}/api/updates/1`)).json()).status,
    ).toBe("IGNORED");
    await drawer.getByRole("button", { name: "Close update details" }).click();
    await page.reload();
    await expect(card.locator(".status-label")).toHaveText("Ignored");
  } finally {
    await request.patch(`${API}/api/updates/1/status`, {
      data: { status: original.status },
    });
  }
});

test("management stats and oshi create, edit, pause, and delete", async ({
  page,
  request,
}) => {
  await page.goto("/oshi");
  await expect(page.locator(".oshi-table tbody tr")).toHaveCount(3);
  await expect(page.locator(".stat-card strong")).toHaveText([
    "3",
    "10",
    "3",
    "2",
  ]);
  await expect(page.locator(".scoring-rule")).toHaveCount(6);
  await page.screenshot({
    path: "test-results/oshi-management.png",
    fullPage: true,
  });
  let createdId: number | undefined;
  try {
    await page
      .locator(".page-header")
      .getByRole("button", { name: "+ Add oshi", exact: true })
      .click();
    const form = page.getByRole("dialog", { name: "Add an oshi" });
    await form
      .getByLabel("Name", { exact: true })
      .fill("Integration test oshi");
    await form.getByLabel("Type", { exact: true }).selectOption("CHARACTER");
    await form.getByLabel("Priority", { exact: true }).fill("77");
    await form
      .getByRole("button", { name: "+ Add keyword", exact: true })
      .click();
    await form
      .getByRole("textbox", { name: "Keyword 1", exact: true })
      .fill("テスト");
    await form.getByRole("spinbutton", { name: "Keyword 1 weight" }).fill("25");
    await form.getByRole("button", { name: "Add oshi", exact: true }).click();
    await expect(form).not.toBeVisible();
    await expect(page.locator(".oshi-table tbody tr")).toHaveCount(4);
    const oshi: Oshi[] = await (await request.get(`${API}/api/oshi`)).json();
    createdId = oshi.find((item) => item.name === "Integration test oshi")!.id;
    const row = page.locator(`[data-oshi-id="${createdId}"]`);
    await row
      .getByRole("button", { name: "Edit Integration test oshi", exact: true })
      .click();
    const edit = page.getByRole("dialog", { name: "Edit oshi", exact: true });
    await edit.getByLabel("Name", { exact: true }).fill("Edited test oshi");
    await edit.getByLabel("Priority", { exact: true }).fill("88");
    await edit.getByRole("button", { name: "Save changes" }).click();
    await expect(edit).not.toBeVisible();
    await expect(row.locator(".table-oshi-name")).toHaveText(
      "Edited test oshi",
    );
    await row.getByRole("button", { name: "Pause Edited test oshi" }).click();
    await expect(
      row.getByRole("button", { name: "Activate Edited test oshi" }),
    ).toBeVisible();
    await page.reload();
    await expect(
      row.getByRole("button", { name: "Activate Edited test oshi" }),
    ).toBeVisible();
    await row.getByRole("button", { name: "Delete Edited test oshi" }).click();
    const confirmation = page.getByRole("dialog", {
      name: "Remove Edited test oshi?",
    });
    await confirmation
      .getByRole("button", { name: "Remove oshi", exact: true })
      .click();
    await expect(confirmation).not.toBeVisible();
    await expect(page.locator(".oshi-table tbody tr")).toHaveCount(3);
    expect(
      (await (await request.get(`${API}/api/stats`)).json()).total_updates,
    ).toBe(10);
  } finally {
    if (createdId) await request.delete(`${API}/api/oshi/${createdId}`);
  }
});

test("failed connections and status writes recover without a crash", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route(`${API}/**`, (route) => route.abort("connectionrefused"));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your local backend is offline" }),
  ).toBeVisible();
  await expect(page.locator(".update-card")).toHaveCount(0);
  await page.screenshot({ path: "test-results/offline.png" });
  await page
    .getByRole("link", { name: "Oshi Management", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your local backend is offline" }),
  ).toBeVisible();
  await page.unroute(`${API}/**`);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.locator(".oshi-table tbody tr")).toHaveCount(3);
  await page.goto("/");
  await expect(page.locator(".update-card")).toHaveCount(10);
  const original: Update = await (
    await request.get(`${API}/api/updates/1`)
  ).json();
  await page.route(`${API}/api/updates/1/status`, (route) =>
    route.abort("connectionrefused"),
  );
  await page
    .locator('[data-update-id="1"]')
    .getByRole("button", { name: "Save", exact: true })
    .click();
  await expect(page.locator(".inline-error[role='alert']")).toContainText(
    "The local API is unavailable",
  );
  expect(
    (await (await request.get(`${API}/api/updates/1`)).json()).status,
  ).toBe(original.status);
  expect(errors).toEqual([]);
});

test("desktop and tablet widths preserve content without document overflow", async ({
  page,
}) => {
  for (const width of [1440, 1200, 1024, 768]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const route of ["/", "/oshi"]) {
      await page.goto(route);
      await expect(
        page
          .locator(route === "/" ? ".update-card" : ".oshi-table tbody tr")
          .first(),
      ).toBeVisible();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
        `Document overflow at ${width}px on ${route}`,
      ).toBeLessThanOrEqual(width);
    }
  }
});

test("pagination expands client-side search using additional real API pages", async ({
  page,
  request,
}) => {
  // This disposable database is removed when the test backend shuts down.
  const create = (title: string) =>
    request.post(`${API}/api/updates`, {
      data: {
        title,
        summary: "Pagination verification",
        category: "NEWS",
        source: "Integration test",
        source_url: "https://example.invalid/integration-pagination",
      },
    });
  expect((await create("Pagination target on a later page")).status()).toBe(
    201,
  );
  for (let index = 0; index < 50; index++) {
    expect((await create(`Additional update ${index}`)).status()).toBe(201);
  }
  await page.goto("/?category=NEWS");
  await expect(page.locator(".update-card")).toHaveCount(50);
  await page.getByRole("searchbox").fill("Pagination target");
  await expect(
    page.getByText("No matches in your loaded updates"),
  ).toBeVisible();
  await expect(
    page.getByText("Searching 50 loaded updates.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Load more updates" }).click();
  await expect(page.locator(".update-card")).toHaveCount(1);
  await expect(
    page.getByRole("button", {
      name: "Pagination target on a later page",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Load more updates" }),
  ).not.toBeVisible();
});
