<script lang="ts">
  import Router, { push } from 'svelte-spa-router'
  import { onMount } from 'svelte'
  import { get } from 'svelte/store'

  import HomePage from './HomePage.svelte'
  import AboutPage from './AboutPage.svelte'
  import ChatbotPage from './ChatbotPage.svelte'
  import ArchivePage from './ArchivePage.svelte'
  import SettingsPage from './SettingsPage.svelte'
  import LoginPage from './LoginPage.svelte'
  import DocumentEditorPage from './DocumentEditorPage.svelte'
  import AdminUsersPage from './AdminUsersPage.svelte'
  import ActivityLogsPage from './ActivityLogsPage.svelte'
  import { authReady, currentUser, initAuth } from './lib/auth'

  const authRoutes = new Set(['/login', '/register'])
  const adminOnlyRoutes = ['/settings', '/admin/users', '/admin/activity']

  const routes = {
    '/': HomePage,
    '/about': AboutPage,
    '/assistant': ChatbotPage,
    '/archive': ArchivePage,
    '/settings': SettingsPage,
    '/admin/users': AdminUsersPage,
    '/admin/activity': ActivityLogsPage,
    '/login': LoginPage,
    '/documents/:id': DocumentEditorPage,
    '/documents/:id/editor': DocumentEditorPage
  }

  function getCurrentPath() {
    const hash = window.location.hash || '#/'
    const normalized = hash.startsWith('#') ? hash.slice(1) : hash
    return normalized || '/'
  }

  function enforceRoute(path: string) {
    if (!get(authReady)) return
    const user = get(currentUser)
    const isAuthenticated = Boolean(user?.is_authenticated)
    const isAdmin = isAuthenticated && user?.role === 'admin'
    if (adminOnlyRoutes.includes(path) && !isAdmin) {
      push('/')
      return
    }
    if (isAuthenticated && authRoutes.has(path)) {
      push('/')
      return
    }
    if (!isAuthenticated && path === '/register') {
      push('/login')
    }
  }

  onMount(() => {
    const handleHashChange = () => enforceRoute(getCurrentPath())

    initAuth().then(handleHashChange)
    window.addEventListener('hashchange', handleHashChange)

    const unsubscribeCurrentUser = currentUser.subscribe(() => {
      handleHashChange()
    })

    return () => {
      window.removeEventListener('hashchange', handleHashChange)
      unsubscribeCurrentUser()
    }
  })
</script>

{#if $authReady}
  <Router {routes} />
{:else}
  <div class="auth-wrap"><p>Loading...</p></div>
{/if}
