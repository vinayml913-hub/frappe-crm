import { dayjs } from 'frappe-ui'

export function getLastXDays(range: number = 30): string | null {
  const today = new Date()
  const lastXDate = new Date(today)
  lastXDate.setDate(today.getDate() - range)

  return `${dayjs(lastXDate).format('YYYY-MM-DD')},${dayjs(today).format(
    'YYYY-MM-DD',
  )}`
}

// Company financial quarters (NOT calendar quarters):
//   Q1 = Mar 1 - May 31
//   Q2 = Jun 1 - Aug 31
//   Q3 = Sep 1 - Nov 30
//   Q4 = Dec 1 - Feb 28/29 (crosses into the following calendar year)
const QUARTER_MONTHS: Record<string, [number, number, number]> = {
  Q1: [2, 4, 0], // Mar (0-indexed month 2) - May, same year
  Q2: [5, 7, 0], // Jun - Aug, same year
  Q3: [8, 10, 0], // Sep - Nov, same year
  Q4: [11, 1, 1], // Dec (same year) - Feb (following year)
}

// Given today's date, resolve which financial quarter it falls in and the
// fiscal year that quarter belongs to (the year of the quarter's start month).
export function getCurrentFinancialQuarter(): { quarter: string; year: number } {
  const today = new Date()
  const month = today.getMonth() // 0-indexed
  const year = today.getFullYear()

  if (month >= 2 && month <= 4) return { quarter: 'Q1', year }
  if (month >= 5 && month <= 7) return { quarter: 'Q2', year }
  if (month >= 8 && month <= 10) return { quarter: 'Q3', year }
  // Dec (11), Jan (0), Feb (1)
  if (month === 11) return { quarter: 'Q4', year }
  return { quarter: 'Q4', year: year - 1 }
}

export function getQuarterRange(quarter: string, fiscalYear?: number): string {
  const { year: currentFiscalYear } = getCurrentFinancialQuarter()
  const year = fiscalYear ?? currentFiscalYear
  const [startMonth, endMonth, endYearOffset] = QUARTER_MONTHS[quarter]

  const from = new Date(year, startMonth, 1)
  const to = new Date(year + endYearOffset, endMonth + 1, 0) // last day of endMonth

  return `${dayjs(from).format('YYYY-MM-DD')},${dayjs(to).format('YYYY-MM-DD')}`
}

export function formatter(range: string) {
  const [from, to] = range.split(',')
  return `${formatRange(from)} to ${formatRange(to)}`
}

export function formatRange(date: string) {
  const dateObj = new Date(date)
  return dateObj.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year:
      dateObj.getFullYear() === new Date().getFullYear()
        ? undefined
        : 'numeric',
  })
}
