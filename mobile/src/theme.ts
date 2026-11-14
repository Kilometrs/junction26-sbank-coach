// Colours and type from the "Personal Economic Trainer – chatbot mockup" design (S-mobiili style).
import { TextStyle } from 'react-native';

export const colors = {
  green: '#007841',
  greenDark: '#004628',
  mint: '#EBF7EC',
  white: '#FFFFFF',
  ink: '#1F1F1F',
  heading: '#25262A',
  muted: '#666666',
  line: '#E3E6E4',
  border: '#C1C1C1',
  grey: '#949494',
  chip: '#EFF0F2',
  warnBg: '#FFF1CC',
  warnInk: '#5C4300',
  webBackdrop: '#D5E4D8',
};

/** On web and tablets the app is a centred phone-width column. */
export const PHONE_MAX_WIDTH = 430;

const families = {
  400: 'Inter_400Regular',
  500: 'Inter_500Medium',
  600: 'Inter_600SemiBold',
  700: 'Inter_700Bold',
} as const;

/** Text style with Inter at a given size and weight (custom fonts need one family per weight). */
export function font(size: number, weight: keyof typeof families = 400, color: string = colors.ink): TextStyle {
  return { fontFamily: families[weight], fontSize: size, color };
}

/** €1 050 style, Finnish thousands spacing. Pass sign=true for +€/−€. */
export function eur(value: number, sign = false): string {
  const n = Math.round(value);
  const digits = String(Math.abs(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const prefix = n < 0 ? '−' : sign ? '+' : '';
  return `${prefix}€${digits}`;
}

const DAYS_PER_MONTH = 365.25 / 12;

/** Whole months plus the leftover fraction as days: 3.5 → { whole: 3, days: 15 }. */
function splitMonths(value: number) {
  const abs = Math.abs(value);
  let whole = Math.floor(abs);
  let days = Math.round((abs - whole) * DAYS_PER_MONTH);
  if (days >= 30) {
    whole += 1;
    days = 0;
  }
  return { sign: value < 0 && (whole > 0 || days > 0) ? '−' : '', whole, days };
}

/** Over a year: whole years and the remaining whole months, 15.4 → { years: 1, rest: 3 }. Days are too fine at that scale. */
function splitYears(value: number) {
  const total = Math.round(Math.abs(value));
  return { sign: value < 0 ? '−' : '', years: Math.floor(total / 12), rest: total % 12 };
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** "3 months", "3 months 15 days", "15 days"; more than 12 months: "1 year 3 months", "2 years". */
export function months(value: number | null | undefined): string {
  if (value === null || value === undefined) return '–';
  if (Math.abs(value) > 12) {
    const { sign, years, rest } = splitYears(value);
    return sign + [plural(years, 'year'), rest > 0 ? plural(rest, 'month') : ''].filter(Boolean).join(' ');
  }
  const { sign, whole, days } = splitMonths(value);
  const parts = [whole > 0 || days === 0 ? plural(whole, 'month') : '', days > 0 ? plural(days, 'day') : ''];
  return sign + parts.filter(Boolean).join(' ');
}

/** Compact form for chart labels: "3 mo", "3 mo 15 d", "15 d"; more than 12 months: "1 y 3 mo", "2 y". */
export function monthsShort(value: number): string {
  if (Math.abs(value) > 12) {
    const { sign, years, rest } = splitYears(value);
    return sign + [`${years} y`, rest > 0 ? `${rest} mo` : ''].filter(Boolean).join(' ');
  }
  const { sign, whole, days } = splitMonths(value);
  const parts = [whole > 0 || days === 0 ? `${whole} mo` : '', days > 0 ? `${days} d` : ''];
  return sign + parts.filter(Boolean).join(' ');
}
