import type { components } from './schema'

type Schemas = components['schemas']

export type DaySummary = Schemas['DaySummary']
export type LoggedEntry = Schemas['LoggedEntry']
export type ProgressItem = Schemas['ProgressItem']
export type WeightTrend = Schemas['WeightTrend']
export type WeightPoint = Schemas['WeightPoint']
export type GoalsInfo = Schemas['GoalsInfo']
export type GoalInfo = Schemas['GoalInfo']
export type FoodCandidate = Schemas['FoodCandidate']
export type FoodSearchResult = Schemas['FoodSearchResult']

// Request bodies of the write endpoints
export type NewEntry = Schemas['NewEntry']
export type EntryChange = Schemas['EntryChange']
export type FoodValues = Schemas['FoodValues']
export type WeightIn = Schemas['WeightIn']
export type GoalIn = Schemas['GoalIn']
