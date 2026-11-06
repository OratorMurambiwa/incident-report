import test from "node:test";
import assert from "node:assert/strict";
import { validate, modeLabel, listQuery } from "./domain.js";
const valid = {
  service: "payments",
  title: "Database timeout",
  description: "Connections exhausted",
  severity: "HIGH",
};
test("valid submission accepted", () => assert.deepEqual(validate(valid), {}));
test("whitespace-only fields rejected", () =>
  assert.equal(
    Object.keys(
      validate({ ...valid, service: "  ", title: " ", description: "\n" }),
    ).length,
    3,
  ));
test("server length limits enforced", () =>
  assert.equal(
    Object.keys(
      validate({
        ...valid,
        service: "x".repeat(101),
        title: "x".repeat(201),
        description: "x".repeat(10001),
      }),
    ).length,
    3,
  ));
test("invalid severity rejected", () =>
  assert.ok(validate({ ...valid, severity: "URGENT" }).severity));
test("retrieval explicitly differentiated from generation", () => {
  assert.equal(modeLabel("RETRIEVAL_ONLY"), "Retrieved evidence only");
  assert.equal(modeLabel("GENERATED"), "AI-generated diagnosis");
  assert.equal(modeLabel("LEGACY"), "Legacy diagnosis");
});
test("filters encoded without losing literal service characters", () => {
  const q = new URL(
    "http://local" + listQuery(2, "HIGH", "FAILED", " db & cache% "),
  );
  assert.equal(q.searchParams.get("service"), "db & cache%");
  assert.equal(q.searchParams.get("page"), "2");
  assert.equal(q.searchParams.get("severity"), "HIGH");
  assert.equal(q.searchParams.get("status"), "FAILED");
});
test("empty filters omitted", () =>
  assert.equal(listQuery(0, "", "", "  "), "/api/incidents?page=0&size=20"));
