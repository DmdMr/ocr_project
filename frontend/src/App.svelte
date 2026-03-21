<script>
  import Router from 'svelte-spa-router'
  import HomePage from './HomePage.svelte'
  import AboutPage from './AboutPage.svelte'

  const routes = {
    '/': HomePage,
    '/about': AboutPage
  }
</script>

<Router {routes} />

