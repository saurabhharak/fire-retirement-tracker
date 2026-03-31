export function formatIndian(amount: number): string {
  const isNeg = amount < 0;
  const n = Math.round(Math.abs(amount));
  const s = String(n);

  if (s.length <= 3) return isNeg ? `-${s}` : s;

  const last3 = s.slice(-3);
  let remaining = s.slice(0, -3);
  const groups: string[] = [];

  while (remaining.length > 2) {
    groups.push(remaining.slice(-2));
    remaining = remaining.slice(0, -2);
  }
  if (remaining) groups.push(remaining);
  groups.reverse();

  const result = groups.join(",") + "," + last3;
  return isNeg ? `-${result}` : result;
}

export function formatRupees(amount: number): string {
  return `\u20B9${formatIndian(amount)}`;
}
