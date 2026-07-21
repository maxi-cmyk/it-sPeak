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
