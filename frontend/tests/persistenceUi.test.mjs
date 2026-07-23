import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { eligibleReplacementSessions, projectFromApi } from "../lib/persistenceUi.mjs";

test("project API rows map improvement areas onto the card contract", () => {
  const project = projectFromApi({ id: "p1", goal: "Prepare the pitch", default_archetype_key: "corporate_board", deadline: null, improvement_areas: ["pacing", "gestures"] });
  assert.equal(project.description, "Prepare the pitch");
  assert.equal(project.archetype, "corporate_board");
  assert.equal(project.deadline, "");
  assert.deepEqual(project.improvementAreas, ["pacing", "gestures"]);
});

test("replacement choices defensively exclude Session 1 and retired sessions", () => {
  const choices = eligibleReplacementSessions([
    { id: "s1", sequence_number: 1, status: "success", retired_at: null },
    { id: "s2", sequence_number: 2, status: "success", retired_at: null },
    { id: "s3", sequence_number: 3, status: "replaced", retired_at: "2026-01-01" },
  ]);
  assert.deepEqual(choices.map((session) => session.id), ["s2"]);
});

test("dashboard and project routes no longer import fixture projects", async () => {
  const dashboard = await readFile(new URL("../app/page.js", import.meta.url), "utf8");
  const project = await readFile(new URL("../app/project/[id]/page.js", import.meta.url), "utf8");
  assert.equal(dashboard.includes("initialProjects"), false);
  assert.equal(project.includes("initialProjects"), false);
});

test("project cards display session capacity", async () => {
  const card = await readFile(new URL("../components/ProjectCard.js", import.meta.url), "utf8");
  assert.equal(card.includes("Number(project.session_count)"), true);
  assert.equal(card.includes(">Sessions</span>"), true);
  assert.equal(card.includes("Retained sessions"), false);
  assert.equal(card.includes("Array.from({ length: 5 }"), true);
  assert.equal(card.includes('role="link"'), false);
  assert.equal(card.includes("aria-expanded={menuOpen}"), true);
  assert.equal(card.includes('days === 0 ? "Due today"'), true);
});

test("project folder exposes one first-session action and an editor", async () => {
  const project = await readFile(new URL("../app/project/[id]/page.js", import.meta.url), "utf8");
  assert.equal(project.match(/Add first session/g)?.length, 1);
  assert.equal(project.includes("Start session 1"), false);
  assert.equal(project.includes("Edit project"), true);
  assert.equal(project.includes("updateProject(id"), true);
  assert.equal(project.includes("Session 1 is used as the baseline for your progress."), true);
  assert.equal(project.includes("The scoring profile applied"), false);
  assert.equal(project.includes("protected"), false);
  assert.equal(project.includes("retained"), false);
  assert.equal(project.includes("Selected coaching focus"), false);
  assert.equal(project.includes("Pillar progress"), false);
});

test("project editor uses accessible selection icons and themed date control", async () => {
  const editor = await readFile(new URL("../components/AddProjectModal.js", import.meta.url), "utf8");
  assert.equal(editor.includes("Project description"), true);
  assert.equal(editor.includes("Rehearsal goal"), false);
  assert.equal(editor.includes("ImprovementAreaIcon"), true);
  assert.equal(editor.includes("date-control"), true);
});

test("dashboard and project headers omit the removed introductory copy", async () => {
  const dashboard = await readFile(new URL("../app/page.js", import.meta.url), "utf8");
  const project = await readFile(new URL("../app/project/[id]/page.js", import.meta.url), "utf8");
  assert.equal(dashboard.includes("Your rehearsal projects"), false);
  assert.equal(dashboard.includes("Track each baseline"), false);
  assert.equal(dashboard.includes('<h1 className="page-title">Practice archive</h1>'), true);
  assert.equal(project.includes("Project ·"), false);
});
