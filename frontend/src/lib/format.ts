// format.ts — small display helpers.

export function money(n: number | undefined | null): string {
  if (n == null) return '—'
  return '$' + Math.round(n).toLocaleString('en-US')
}

/** Compact budget cap, e.g. 12000 -> "$12k". */
export function moneyShort(n: number): string {
  if (n >= 1000) return '$' + Math.round(n / 1000) + 'k'
  return '$' + n
}

export function titleCase(s: string): string {
  return s ? s[0].toUpperCase() + s.slice(1) : s
}
