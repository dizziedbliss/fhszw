import { num } from '../format.ts'

// One look for every chart, and for the legend that labels its lines.

export const MARGIN = { top: 8, right: 8, bottom: 0, left: 0 }
export const GRID = { fill: 'var(--paper)', stroke: 'var(--grid)' }
export const AXIS = { stroke: 'var(--grid-major)', tick: { fill: 'var(--ink-2)', fontSize: 14 } }
export const Y_AXIS = { ...AXIS, width: 60, tickFormatter: num }
export const CURSOR = { stroke: 'var(--ink-2)', strokeDasharray: '3 3' }

/** Recorder pens: solid blue for the forecast, dashed green for what was metered. */
export const PENS = {
  forecast: { stroke: 'var(--pen-forecast)', strokeWidth: 2 },
  actual: { stroke: 'var(--pen-actual)', strokeWidth: 2, strokeDasharray: '5 3' },
} as const

/** Each value covers its whole period, so lines step rather than slope. */
export const STEPS = {
  type: 'stepAfter',
  dot: false,
  activeDot: false,
  isAnimationActive: false,
} as const

/** The switch every chart has: the same data as a chart or as a table. */
export const CHART_OR_TABLE = [
  { value: 'chart', label: 'Chart' },
  { value: 'table', label: 'Table' },
] as const
export type ChartOrTable = (typeof CHART_OR_TABLE)[number]['value']
