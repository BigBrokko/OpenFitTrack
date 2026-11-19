import type { DaySummary, GoalInfo, GoalsInfo, WeightTrend } from '../api/types'

export const goal: GoalInfo = {
  valid_from: '2026-11-01',
  kcal: 2000,
  protein_g: 160,
  carbs_g: 50,
  fat_g: 70,
  target_weight_kg: 80,
}

/** A day with two entries, below the goal for most values and over it for carbohydrates. */
export function dayFixture(overrides: Partial<DaySummary> = {}): DaySummary {
  return {
    date: '2026-11-11',
    totals: { kcal: 894.2, protein_g: 36.4, carbs_g: 88.9, fat_g: 40.2 },
    goal,
    progress: {
      kcal: { eaten: 894.2, goal: 2000, remaining: 1105.8, percent: 44.7 },
      protein_g: { eaten: 36.4, goal: 160, remaining: 123.6, percent: 22.8 },
      carbs_g: { eaten: 88.9, goal: 50, remaining: -38.9, percent: 177.8 },
      fat_g: { eaten: 40.2, goal: 70, remaining: 29.8, percent: 57.4 },
    },
    entries: [
      {
        id: 1,
        time: '08:30',
        food: 'Kwark volle',
        amount_g: 200,
        nutrients: { kcal: 236, protein_g: 15, carbs_g: 7.2, fat_g: 16 },
      },
      {
        id: 2,
        time: '12:15',
        food: 'Banaan',
        amount_g: 100,
        nutrients: { kcal: 92, protein_g: 1.1, carbs_g: 20, fat_g: 0.3 },
      },
    ],
    note: null,
    ...overrides,
  }
}

export const emptyDay = dayFixture({
  totals: { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
  progress: {
    kcal: { eaten: 0, goal: 2000, remaining: 2000, percent: 0 },
    protein_g: { eaten: 0, goal: 160, remaining: 160, percent: 0 },
    carbs_g: { eaten: 0, goal: 50, remaining: 50, percent: 0 },
    fat_g: { eaten: 0, goal: 70, remaining: 70, percent: 0 },
  },
  entries: [],
  note: 'Nothing is logged on this day. That does not mean nothing was eaten.',
})

export function weightFixture(overrides: Partial<WeightTrend> = {}): WeightTrend {
  return {
    points: [
      { date: '2026-10-01', weight_kg: 84, trend_kg: 84 },
      { date: '2026-10-20', weight_kg: 83, trend_kg: 83.4 },
      { date: '2026-11-10', weight_kg: 82, trend_kg: 82.6 },
    ],
    measurements_total: 3,
    latest_weight_kg: 82,
    latest_trend_kg: 82.6,
    trend_change_7d_kg: -0.2,
    target_weight_kg: 80,
    ...overrides,
  }
}

export const noWeights = weightFixture({
  points: [],
  measurements_total: 0,
  latest_weight_kg: null,
  latest_trend_kg: null,
  trend_change_7d_kg: null,
  target_weight_kg: null,
})

export const goalsFixture: GoalsInfo = {
  current: goal,
  history: [
    goal,
    {
      valid_from: '2026-09-03',
      kcal: 2200,
      protein_g: 150,
      carbs_g: 250,
      fat_g: 70,
      target_weight_kg: null,
    },
  ],
}

export const noGoals: GoalsInfo = { current: null, history: [] }
