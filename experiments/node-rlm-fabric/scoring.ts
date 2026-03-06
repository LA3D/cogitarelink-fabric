export function substringMatch(
  predicted: string,
  expected: string | string[],
): number {
  const lower = predicted.toLowerCase();
  const targets = Array.isArray(expected) ? expected : [expected];
  return targets.some((e) => lower.includes(e.toLowerCase())) ? 1.0 : 0.0;
}
