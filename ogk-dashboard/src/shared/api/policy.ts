/*
 * Policy calls used by both policy (overview, history) and screentime (editing).
 * Features cannot import each other, so they share these through shared/.
 */
import { apiFetch } from '@/shared/api/client.ts'
import type { Child } from '@/shared/types/family.ts'
import type { Policy, PolicyUpdate, PolicyVersion } from '@/shared/types/policy.ts'

export const policyKey = (childId: number) => ['policy', childId] as const
export const policyVersionsKey = (childId: number) => ['policy', childId, 'versions'] as const
export const policyChildKey = (childId: number) => ['children', childId] as const

export const getPolicy = (childId: number) => apiFetch<Policy>(`/api/children/${childId}/policy`)

export const updatePolicy = (childId: number, body: PolicyUpdate) =>
  apiFetch<Policy>(`/api/children/${childId}/policy`, { method: 'PATCH', json: body })

export const listPolicyVersions = (childId: number) =>
  apiFetch<PolicyVersion[]>(`/api/children/${childId}/policy/versions`)

export const getPolicyChild = (childId: number) => apiFetch<Child>(`/api/children/${childId}`)
