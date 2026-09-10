// FIXTURE - deliberately LEGAL. The control case: if this one also failed, the guard
// would be proving nothing except that ESLint dislikes the fixtures directory.
export function add(a: number, b: number): number {
  return a + b;
}
