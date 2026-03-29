import { get, writable } from 'svelte/store'
import { getCurrentUser, login as apiLogin, logout as apiLogout, register as apiRegister, type AuthUser } from './api'

export const currentUser = writable<AuthUser | null>(null)
export const authReady = writable(false)

export async function initAuth() {
  try {
    const user = await getCurrentUser()
    currentUser.set(user)
  } finally {
    authReady.set(true)
  }
}

export async function login(username: string, password: string) {
  const user = await apiLogin(username, password)
  currentUser.set(user)
  return user
}

export async function register(username: string, password: string) {
  const user = await apiRegister(username, password)
  currentUser.set(user)
  return user
}

export async function logout() {
  await apiLogout()
  currentUser.set(null)
}

export function isAuthenticated() {
  return !!get(currentUser)
}
