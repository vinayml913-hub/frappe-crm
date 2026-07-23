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
//   Q1 = Apr 1 - Jun 30
//   Q2 = Jul 1 - Sep 30
//   Q3 = Oct 1 - Dec 31
//   Q4 = Jan 1 - Mar 31 (crosses into the following calendar year)
const QUARTER_MONTHS: Record<string, [number, number, number]> = {
  Q1: [3, 5, 0], // Apr (0-indexed month 3) - Jun, same year
  Q2: [6, 8, 0], // Jul - Sep, same year
  Q3: [9, 11, 0], // Oct - Dec, same year
  Q4: [0, 2, 1], // Jan - Mar, following year
}

// Given today's date, resolve which financial quarter it falls in and the
// fiscal year that quarter belongs to (the year of the quarter's start month,
// i.e. the year the Apr-Dec portion of the fiscal year started in).
export function getCurrentFinancialQuarter(): { quarter: string; year: number } {
  const today = new Date()
  const month = today.getMonth() // 0-indexed
  const year = today.getFullYear()

  if (month >= 3 && month <= 5) return { quarter: 'Q1', year }
  if (month >= 6 && month <= 8) return { quarter: 'Q2', year }
  if (month >= 9 && month <= 11) return { quarter: 'Q3', year }
  // Jan (0), Feb (1), Mar (2)
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
