<script>
  import Router from 'svelte-spa-router'
  import HomePage from './HomePage.svelte'
  import AboutPage from './AboutPage.svelte'
  import ChatbotPage from './ChatbotPage.svelte'
  import ArchivePage from './ArchivePage.svelte'

  const routes = {
    '/': HomePage,
    '/about': AboutPage,
    '/assistant': ChatbotPage,
    '/archive': ArchivePage
  }
</script>

<Router {routes} />
