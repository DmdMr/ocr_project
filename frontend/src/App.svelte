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
  import RegisterPage from './RegisterPage.svelte'
  import DocumentPage from './DocumentPage.svelte'
  import { authReady, currentUser, initAuth } from './lib/auth'

  const publicRoutes = new Set(['/login', '/register'])

  const routes = {
    '/': HomePage,
    '/about': AboutPage,
    '/assistant': ChatbotPage,
    '/archive': ArchivePage,
    '/settings': SettingsPage,
    '/login': LoginPage,
    '/register': RegisterPage,
    '/document/:id/:slug': DocumentPage,
    '/document/:id': DocumentPage
  }

  function currentPath() {
    if (typeof window === 'undefined') return '/'
    const hash = window.location.hash || ''
    if (hash.startsWith('#/')) return hash.slice(1)
    return window.location.pathname || '/'
  }

  function isPublicRoute(path: string) {
    if (publicRoutes.has(path)) return true
    return [...publicRoutes].some((route) => path.startsWith(`${route}/`))
  }

  function enforceRoute(path: string) {
    if (!get(authReady)) return
    const user = get(currentUser)
    const routeIsPublic = isPublicRoute(path)

    if (!user && !routeIsPublic) {
      push('/login')
    } else if (user && routeIsPublic) {
      push('/')
    }
  }

  onMount(() => {
    const syncRoute = () => enforceRoute(currentPath())

    void initAuth().then(() => {
      syncRoute()
    })

    window.addEventListener('hashchange', syncRoute)
    window.addEventListener('popstate', syncRoute)

    const unsubscribeUser = currentUser.subscribe(() => syncRoute())

    return () => {
      window.removeEventListener('hashchange', syncRoute)
      window.removeEventListener('popstate', syncRoute)
      unsubscribeUser()
    }
  })
</script>

{#if $authReady}
  <Router {routes} />
{:else}
  <div class="auth-wrap"><p>Loading...</p></div>
{/if}
