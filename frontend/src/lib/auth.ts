import { derived, writable } from 'svelte/store'
import { getCurrentUser, login as apiLogin, logout as apiLogout, register as apiRegister, type AuthUser } from './api'

const viewerUser: AuthUser = {
  id: null,
  username: null,
  role: 'viewer',
  is_authenticated: false,
  is_active: true
}

function normalizeAuthUser(user: AuthUser | null, defaultAuthenticated = false): AuthUser {
  if (!user) return viewerUser
  const role = user.role ?? (user.id ? 'editor' : 'viewer')
  const isAuthenticated = typeof user.is_authenticated === 'boolean'
    ? user.is_authenticated
    : (defaultAuthenticated || Boolean(user.id))
  return {
    ...viewerUser,
    ...user,
    role,
    is_authenticated: isAuthenticated
  }
}

export const currentUser = writable<AuthUser>(viewerUser)
export const authReady = writable(false)
export const isAuthenticated = derived(currentUser, ($currentUser) => Boolean($currentUser.is_authenticated))
export const isAdmin = derived(currentUser, ($currentUser) => $currentUser.role === 'admin' && Boolean($currentUser.is_authenticated))
export const canEditDocuments = derived(
  currentUser,
  ($currentUser) => Boolean($currentUser.is_authenticated) && ($currentUser.role === 'editor' || $currentUser.role === 'admin')
)
export const roleLabel = derived(currentUser, ($currentUser) => $currentUser.role)

export async function initAuth() {
  try {
    const user = await getCurrentUser()
    currentUser.set(normalizeAuthUser(user))
  } finally {
    authReady.set(true)
  }
}

export async function login(username: string, password: string) {
  const user = await apiLogin(username, password)
  currentUser.set(normalizeAuthUser(user, true))
  return user
}

export async function register(username: string, password: string) {
  const user = await apiRegister(username, password)
  currentUser.set(normalizeAuthUser(user, true))
  return user
}

export async function logout() {
  await apiLogout()
  currentUser.set(viewerUser)
}
