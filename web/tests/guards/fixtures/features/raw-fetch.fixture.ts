// FIXTURE - deliberately illegal. See deep-import.fixture.ts for why this exists.
//
// Violation: raw HTTP outside src/shared/api.
export async function loadProjects() {
  const response = await fetch('/api/v1/projects');
  return response.json();
}
