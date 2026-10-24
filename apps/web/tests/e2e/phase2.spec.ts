import { test, expect } from "@playwright/test";

// Synthetic data only. Run against compose.test.yaml, never an actual clinic.
async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page
    .getByLabel("Email", { exact: true })
    .fill("admin@harbordentaldemo.local");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.E2E_PASSWORD ?? "Phase1Synthetic123!");
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page).toHaveURL(/dashboard/);
}

test("patient profile, follow-up and recall workflows", async ({ page }) => {
  const firstName = "PhaseTwo" + Date.now();
  await login(page);
  await page.getByRole("button", { name: "Patients", exact: true }).click();
  await page.getByRole("button", { name: "Add patient", exact: true }).click();
  const form = page.getByRole("form", { name: "Patient form" });
  await form.getByLabel("first name", { exact: true }).fill(firstName);
  await form.getByLabel("last name", { exact: true }).fill("Synthetic");
  await form.getByLabel("phone", { exact: true }).fill("+12025550199");
  await form.getByRole("button", { name: "Save patient", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: firstName + " Synthetic", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Timeline", exact: true }).click();
  await expect(page.getByRole("tabpanel", { name: "Timeline" })).toContainText(
    "registered",
  );
  await page.getByRole("tab", { name: "Appointments", exact: true }).click();
  await expect(
    page.getByText("No appointments recorded.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Follow-ups", exact: true }).click();
  await page
    .getByRole("button", { name: "New follow-up", exact: true })
    .click();
  const follow = page.getByRole("form", { name: "Follow-up form" });
  await follow
    .getByRole("combobox", { name: "Patient", exact: true })
    .selectOption({ label: firstName + " Synthetic" });
  await follow
    .getByLabel("Reason", { exact: true })
    .fill(firstName + " callback");
  await follow
    .getByLabel("Due time (device timezone)", { exact: true })
    .fill("2020-01-01T10:00");
  await follow
    .getByRole("button", { name: "Save follow-up", exact: true })
    .click();
  const row = page
    .locator("article")
    .filter({ hasText: firstName + " callback" });
  await expect(row).toContainText("pending");
  await row.getByRole("button", { name: "View / edit", exact: true }).click();
  await follow
    .getByRole("combobox", { name: "Status", exact: true })
    .selectOption("completed");
  page.once("dialog", (d) => d.accept());
  await follow
    .getByRole("button", { name: "Save follow-up", exact: true })
    .click();
  await expect(row).toContainText("completed");
  await page.getByRole("button", { name: "Recalls", exact: true }).click();
  await page.getByRole("button", { name: "New recall", exact: true }).click();
  const recall = page.getByRole("form", { name: "Recall form" });
  await recall
    .getByRole("combobox", { name: "Patient", exact: true })
    .selectOption({ label: firstName + " Synthetic" });
  await recall
    .getByLabel("Type", { exact: true })
    .fill("Synthetic clinician request");
  await recall
    .getByLabel("Approved due date", { exact: true })
    .fill("2020-01-01");
  await recall
    .getByRole("button", { name: "Save recall", exact: true })
    .click();
  await expect(
    page.getByText("Synthetic clinician request", { exact: false }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Prepare sandbox reminders", exact: true })
    .click();
  await expect(page.getByText(/0 messages sent\./)).toBeVisible();
  await page.screenshot({
    path: "test-results/phase2-recalls-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect((await page.getByRole("main").boundingBox())?.width).toBeGreaterThan(300);
  await page.screenshot({
    path: "test-results/phase2-recalls-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("estimate creation, recorded approval, version preservation and PDF", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("button", { name: "Estimates", exact: true }).click();
  await page
    .getByRole("button", { name: "Clinic estimate policy", exact: true })
    .click();
  await page.getByLabel("max discount percent", { exact: true }).fill("20");
  await page
    .getByRole("textbox", {
      name: "Approved tax labels and rates (JSON)",
      exact: true,
    })
    .fill('{"none":"0","standard":"10"}');
  await page
    .getByRole("textbox", { name: "Clinic terms", exact: true })
    .fill("Synthetic test estimate; no invoice or signature.");
  await page
    .getByLabel("I confirm these settings are approved by this clinic.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Save approved policy", exact: true })
    .click();
  await page.getByRole("button", { name: "New estimate", exact: true }).click();
  const form = page.getByRole("form", { name: "Estimate form" });
  await form
    .getByRole("combobox", { name: "Patient", exact: true })
    .selectOption({ index: 1 });
  await form
    .getByRole("combobox", { name: "Treatment", exact: true })
    .selectOption({ index: 1 });
  await form.getByLabel("quantity", { exact: true }).fill("3");
  await form
    .getByLabel("Unit price (blank uses catalog)", { exact: true })
    .fill("0.10");
  await form.getByLabel("discount percent", { exact: true }).fill("10");
  await form
    .getByRole("combobox", { name: "Tax treatment", exact: true })
    .selectOption("standard");
  await form
    .getByRole("button", { name: "Review backend totals", exact: true })
    .click();
  await expect(form.getByRole("status")).toContainText("Total 0.30 USD");
  await form.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Record delivery", exact: true }),
  ).toBeVisible();
  page.on("dialog", (d) =>
    d.accept(d.type() === "prompt" ? "Synthetic in-clinic record" : undefined),
  );
  await page
    .getByRole("button", { name: "Record delivery", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Record acceptance", exact: true })
    .click();
  await expect(page.getByText(/Administrative acknowledgement:/)).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF", exact: true }).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/\.pdf$/);
  await file.saveAs("test-results/phase2-estimate.pdf");
  await page
    .getByRole("button", { name: "Create revision", exact: true })
    .click();
  await form
    .getByLabel("Revision reason", { exact: true })
    .fill("Synthetic alternate quotation");
  await form.getByRole("button", { name: "Save draft", exact: true }).click();
  await page
    .getByRole("button", { name: "View version 1", exact: true })
    .click();
  await expect(page.getByText(/Administrative acknowledgement:/)).toBeVisible();
  await page.screenshot({
    path: "test-results/phase2-estimate-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect((await page.getByRole("main").boundingBox())?.width).toBeGreaterThan(300);
  await page.screenshot({
    path: "test-results/phase2-estimate-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test('read-only capability response hides patient mutation and financial navigation', async ({page}) => {
  // UI visibility is isolated here; actual role denials are exercised by backend tests.
  await page.route('**/api/v1/operations/capabilities', route => route.fulfill({
    json:{permissions:['patient_read','followup_read','recall_read'],timezone:'UTC',currency:'USD'}
  }));
  await login(page);
  await expect(page.getByRole('button',{name:'Estimates',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Patients',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Patient workspace',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Add patient',exact:true})).toHaveCount(0);
  await page.getByRole('textbox',{name:'Search patients',exact:true}).fill('no-such-synthetic-patient');
  await expect(page.getByText('No patients match these filters.',{exact:true})).toBeVisible();
});
