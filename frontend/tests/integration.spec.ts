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
    drawer.getByRole("button", { name: "Demo source", exact: true }),
  ).toBeDisabled();
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

test("preview clicks and drags stay open; outside clicks and X dismiss", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1200 });
  await page.goto("/");
  const opener = page.locator(".card-open").first();
  await opener.click();
  const drawer = page.getByRole("dialog", { name: "Update details" });
  await drawer.locator(".drawer-summary").click();
  await expect(drawer).toBeVisible();
  await drawer.locator(".drawer-title").click();
  await expect(drawer).toBeVisible();
  const bounds = (await drawer.boundingBox())!;
  const inside = { x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height - 12 };
  const outside = { x: bounds.x - 30, y: inside.y };
  await page.mouse.click(inside.x, inside.y);
  await expect(drawer).toBeVisible();
  // Starting inside and releasing outside must not discard the preview either.
  await page.mouse.move(inside.x, inside.y);
  await page.mouse.down();
  await page.mouse.move(outside.x, outside.y, { steps: 5 });
  await page.mouse.up();
  await expect(drawer).toBeVisible();
  await page.mouse.click(outside.x, outside.y);
  await expect(drawer).not.toBeVisible();
  await expect(opener).toBeFocused();
  await opener.click();
  await drawer.getByRole("button", { name: "Close update details" }).click();
  await expect(drawer).not.toBeVisible();

  // The shared modal still dismisses discovery from its real backdrop.
  await page.locator(".sidebar-add").click();
  const discovery = page.getByRole("dialog", { name: "Discover oshi" });
  await discovery.getByRole("searchbox").fill("Higedan");
  await discovery.getByRole("heading", { name: "Official髭男dism", exact: true }).click();
  await expect(discovery).toBeVisible();
  const modalBounds = (await discovery.boundingBox())!;
  await page.mouse.click(modalBounds.x - 20, modalBounds.y + 20);
  await expect(discovery).not.toBeVisible();
});

test("preview and feed scroll independently, and closing preserves the feed position", async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 640 });
  await page.goto("/");
  const opener = page.locator(".card-open").first();
  await opener.click();
  const drawer = page.getByRole("dialog", { name: "Update details" });
  await drawer.locator(".drawer-body").waitFor();
  const close = drawer.getByRole("button", { name: "Close update details" });
  // Wait for entry to settle before exercising real wheel input.
  await close.hover();
  const bounds = (await drawer.boundingBox())!;

  await page.mouse.move(bounds.x - 80, 350);
  await page.mouse.wheel(0, 500);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(400);
  const feedPosition = await page.evaluate(() => window.scrollY);
  await expect(drawer).toBeVisible();
  expect(await drawer.evaluate((element) => element.scrollTop)).toBe(0);

  await page.mouse.move(bounds.x + bounds.width / 2, 350);
  await page.mouse.wheel(0, 1000);
  await expect.poll(() => drawer.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
  await expect(drawer.locator(".drawer-actions")).toBeInViewport();
  await expect(close).toBeInViewport();
  expect(await page.evaluate(() => window.scrollY)).toBe(feedPosition);

  // Repeated scrolling at the preview's edge must not move the feed behind it.
  await page.mouse.wheel(0, 500);
  await page.waitForTimeout(250);
  expect(await page.evaluate(() => window.scrollY)).toBe(feedPosition);
  await close.click();
  await expect(drawer).not.toBeVisible();
  await expect(opener).toBeFocused();
  expect(await page.evaluate(() => window.scrollY)).toBe(feedPosition);

  // Ordinary forms keep their existing page scroll lock.
  await page.getByRole("button", { name: "+ Add oshi", exact: true }).click();
  const discovery = page.getByRole("dialog", { name: "Discover oshi" });
  await expect(discovery).toBeVisible();
  const formPosition = await page.evaluate(() => window.scrollY);
  await page.mouse.move(20, 350);
  await page.mouse.wheel(0, 500);
  await page.waitForTimeout(250);
  expect(await page.evaluate(() => window.scrollY)).toBe(formPosition);
  await page.keyboard.press("Escape");
  await expect(discovery).not.toBeVisible();
  await page.mouse.move(700, 350);
  await page.mouse.wheel(0, 500);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(formPosition);
});

test("preview motion reverses smoothly and reduced motion still dismisses", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/");
  const opener = page.locator(".card-open").first();
  await opener.click();
  const drawer = page.getByRole("dialog", { name: "Update details" });
  await expect.poll(() => drawer.evaluate((element) =>
    element.getAnimations().some((animation) =>
      animation instanceof CSSTransition && animation.transitionProperty === "transform"),
  )).toBe(true);
  const motion = await drawer.evaluate(async (element) => {
    // Stop partway through entry and close there: exit must start from that
    // position, without snapping back to the fully open position first.
    for (const animation of element.getAnimations()) {
      animation.pause();
      animation.currentTime = 200;
    }
    const before = new DOMMatrix(getComputedStyle(element).transform).m41;
    element.querySelector<HTMLButtonElement>('.close-button')!.click();
    await new Promise<void>((resolve) => requestAnimationFrame(() =>
      requestAnimationFrame(() => resolve()),
    ));
    return {
      before,
      after: new DOMMatrix(getComputedStyle(element).transform).m41,
      exitRunning: element.getAnimations().some((animation) =>
        animation instanceof CSSTransition && animation.transitionProperty === "transform" &&
        animation.playState === "running"),
    };
  });
  expect(motion.before).toBeGreaterThan(0);
  expect(motion.after).toBeGreaterThanOrEqual(motion.before - 1);
  expect(motion.exitRunning).toBe(true);
  await expect(drawer).not.toBeVisible();
  await expect(opener).toBeFocused();

  await page.emulateMedia({ reducedMotion: "reduce" });
  await opener.click();
  await expect(drawer).toBeVisible();
  expect(await drawer.evaluate((element) => getComputedStyle(element).transitionDuration))
    .toMatch(/^0s(, 0s)*$/);
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(opener).toBeFocused();
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
    await page.getByRole("button", { name: "+ Add manually", exact: true }).click();
    await form.getByRole("button", { name: "More options", exact: true }).click();
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
    await row.getByRole("button", { name: "Remove Edited test oshi" }).click();
    const confirmation = page.getByRole("dialog", {
      name: "Remove Edited test oshi from My Oshi?",
    });
    await confirmation
      .getByRole("button", { name: "Remove", exact: true })
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

test("removal cancels safely, updates selected oshi immediately, and preserves linked history", async ({
  page,
  request,
}) => {
  const original: Update = await (
    await request.get(`${API}/api/updates/1`)
  ).json();
  const baseline = await (await request.get(`${API}/api/stats`)).json();
  const created: Oshi = await (
    await request.post(`${API}/api/oshi`, {
      data: { name: "Removal test oshi", type: "ARTIST", priority: 70 },
    })
  ).json();
  let release = () => {};
  try {
    await request.patch(`${API}/api/updates/1`, {
      data: { oshi_ids: [...original.oshi_ids, created.id] },
    });
    await page.goto(`/?oshi=${created.id}`);
    await expect(page.locator(".update-card")).toHaveCount(1);
    await page
      .getByRole("link", { name: "Oshi Management", exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`/oshi\\?oshi=${created.id}$`));
    const row = page.locator(`[data-oshi-id="${created.id}"]`);
    const sidebar = page.getByRole("navigation", { name: "My oshi" });
    const open = () =>
      row
        .getByRole("button", { name: `Remove ${created.name}`, exact: true })
        .click();
    const dialog = page.getByRole("dialog", {
      name: `Remove ${created.name} from My Oshi?`,
      exact: true,
    });
    await open();
    await expect(
      dialog.getByText(
        "You'll stop tracking new updates for this oshi. Existing update history will remain.",
      ),
    ).toBeVisible();
    await expect(
      dialog.getByRole("button", { name: "Cancel", exact: true }),
    ).toBeFocused();
    for (let index = 0; index < 5; index++) {
      await page.keyboard.press("Tab");
      expect(
        await dialog.evaluate((element) =>
          element.contains(document.activeElement),
        ),
      ).toBe(true);
    }
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(row).toBeVisible();
    await open();
    await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(
      sidebar.getByRole("link", { name: created.name, exact: true }),
    ).toBeVisible();
    await expect(row).toBeVisible();

    await page.route(`${API}/api/oshi/${created.id}`, (route) =>
      route.fulfill({
        status: 503,
        json: { detail: "Removal temporarily unavailable" },
      }),
    );
    await open();
    await dialog.getByRole("button", { name: "Remove", exact: true }).click();
    await expect(dialog.getByRole("alert")).toContainText(
      "Removal temporarily unavailable",
    );
    await expect(row).toBeVisible();
    await page.unroute(`${API}/api/oshi/${created.id}`);

    // Hold the subsequent list refresh: confirmed deletion must update cached UI immediately.
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route(`${API}/api/oshi`, async (route) => {
      await held;
      await route.continue();
    });
    await dialog.getByRole("button", { name: "Remove", exact: true }).click();
    await expect(dialog).not.toBeVisible();
    await expect(row).toHaveCount(0);
    await expect(
      sidebar.getByRole("link", { name: created.name, exact: true }),
    ).toHaveCount(0);
    await expect(page).toHaveURL(/\/oshi$/);
    release();
    await expect(page.locator(".stat-card strong").first()).toHaveText(
      String(baseline.active_oshi),
    );
    await page.unroute(`${API}/api/oshi`);
    await page.getByRole("link", { name: /^For You\b/ }).click();
    await expect(page.locator('[data-update-id="1"]')).toBeVisible();
    await expect(page.locator(".active-filter")).toHaveCount(0);
    expect(
      (await (await request.get(`${API}/api/stats`)).json()).total_updates,
    ).toBe(baseline.total_updates);
    const retained: Update = await (
      await request.get(`${API}/api/updates/1`)
    ).json();
    expect(retained.oshi_ids).toEqual(original.oshi_ids);
    expect(retained.title).toBe(original.title);
  } finally {
    release();
    if (!page.isClosed()) await page.unrouteAll({ behavior: "ignoreErrors" });
    await request.delete(`${API}/api/oshi/${created.id}`);
    await request.patch(`${API}/api/updates/1`, {
      data: { oshi_ids: original.oshi_ids },
    });
  }
});

test("demo source is disabled based on fixture metadata, independent of title", async ({
  page,
}) => {
  await page.route(`${API}/api/updates/1`, async (route) => {
    const response = await route.fetch();
    await route.fulfill({
      response,
      json: {
        ...(await response.json()),
        title: "Fixture without a title prefix",
      },
    });
  });
  await page.goto("/");
  await page.locator('[data-update-id="1"] .card-open').click();
  const drawer = page.getByRole("dialog", { name: "Update details" });
  await expect(
    drawer.getByRole("heading", { name: "Fixture without a title prefix" }),
  ).toBeVisible();
  await expect(
    drawer.getByText("Demo fixture (fictional)", { exact: true }),
  ).toBeVisible();
  const demoSource = drawer.getByRole("button", {
    name: "Demo source",
    exact: true,
  });
  await expect(demoSource).toBeDisabled();
  await expect(drawer.getByRole("link")).toHaveCount(0);
  const before = page.url();
  const count = page.context().pages().length;
  await demoSource.evaluate((button: HTMLButtonElement) => button.click());
  expect(page.url()).toBe(before);
  expect(page.context().pages().length).toBe(count);
});

test("real source keeps its exact external URL and missing sources never become links", async ({
  page,
  request,
}) => {
  const original: Update = await (
    await request.get(`${API}/api/updates/1`)
  ).json();
  const url =
    "https://example.com/announcements?oshi=one%20two&lang=ja#details";
  try {
    // The title still contains [DEMO]; only explicit source metadata identifies a fixture.
    await request.patch(`${API}/api/updates/1`, {
      data: { source: "Source-link test publisher", source_url: url },
    });
    await page.goto("/");
    await page.locator('[data-update-id="1"] .card-open').click();
    const drawer = page.getByRole("dialog", { name: "Update details" });
    const link = drawer.getByRole("link", { name: /Open source/ });
    await expect(link).toHaveAttribute("href", url);
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(link).toHaveAttribute("rel", /noopener/);
    await expect(link).toHaveAttribute("rel", /noreferrer/);
    for (const missing of [null, ""]) {
      // Defensive read-path test: the stable API normally requires source_url.
      await page.route(`${API}/api/updates/1`, async (route) => {
        const response = await route.fetch();
        await route.fulfill({
          response,
          json: {
            ...(await response.json()),
            source_url: missing,
            summary: "",
            published_at: null,
            deadline: null,
            start_date: null,
            end_date: null,
            location: null,
            relevance_score: 0,
            oshi_ids: [],
          },
        });
      });
      await page.reload();
      await page.locator('[data-update-id="1"] .card-open').click();
      await expect(
        drawer.getByRole("button", { name: "Source unavailable", exact: true }),
      ).toBeDisabled();
      await expect(drawer.getByRole("link")).toHaveCount(0);
      await expect(
        drawer.getByRole("heading", { name: "Action", exact: true }),
      ).toHaveCount(0);
      await expect(
        drawer.getByText("Why this appeared", { exact: true }),
      ).toHaveCount(0);
      await expect(drawer.locator(".drawer-summary")).toHaveCount(0);
      await expect(
        drawer.getByText(/Not provided|TBD|No summary provided/),
      ).toHaveCount(0);
      await page.unroute(`${API}/api/updates/1`);
    }
  } finally {
    await request.patch(`${API}/api/updates/1`, {
      data: { source: original.source, source_url: original.source_url },
    });
  }
});

test("simplified cards keep action information and move secondary details into the drawer", async ({
  page,
  request,
}) => {
  const update: Update = await (
    await request.get(`${API}/api/updates/1`)
  ).json();
  await page.goto("/");
  const card = page.locator('[data-update-id="1"]');
  await expect(
    card.getByRole("button", { name: update.title, exact: true }),
  ).toBeVisible();
  await expect(card.locator(".category-badge")).toHaveText(update.category);
  await expect(card.locator(".oshi-badge")).toHaveCount(update.oshi_ids.length);
  await expect(card.locator(".card-deadline time")).toHaveAttribute(
    "datetime",
    update.deadline!,
  );
  await expect(card.getByText(update.location!, { exact: true })).toBeVisible();
  await expect(card.locator(".card-summary")).toHaveCSS(
    "-webkit-line-clamp",
    "2",
  );
  await expect(card.locator(".priority-score strong")).toHaveText(
    String(update.relevance_score),
  );
  await expect(
    card.getByRole("group", { name: "Update actions" }),
  ).toBeVisible();
  await expect(card.locator(".card-metadata, .card-keywords")).toHaveCount(0);
  await expect(card.getByText(update.source, { exact: true })).toHaveCount(0);
  await expect(
    card.locator(`time[datetime="${update.start_date}"]`),
  ).toHaveCount(0);
  await expect(card.locator(`time[datetime="${update.end_date}"]`)).toHaveCount(
    0,
  );
  await card.locator(".card-open").click();
  const drawer = page.getByRole("dialog", { name: "Update details" });
  await expect(drawer.getByText(update.source, { exact: true })).toBeVisible();
  for (const value of [
    update.start_date,
    update.end_date,
    update.published_at,
  ]) {
    await expect(drawer.locator(`time[datetime="${value}"]`)).toBeVisible();
  }
  const explanation = drawer.locator(".drawer-why");
  await expect(explanation).not.toHaveAttribute("open", "");
  await explanation.locator("summary").focus();
  await page.keyboard.press("Enter");
  await expect(explanation.locator(".drawer-score strong")).toHaveText(
    `${update.relevance_score} / 100`,
  );
  expect(await explanation.locator(".badge").count()).toBeGreaterThan(0);
  for (const action of ["Save", "Interested", "Going", "Ignore"]) {
    await expect(
      drawer.getByRole("button", { name: action, exact: true }),
    ).toBeVisible();
  }
  await page.screenshot({ path: "test-results/simplified-drawer.png" });
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
