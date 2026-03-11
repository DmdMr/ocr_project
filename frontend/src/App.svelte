<script lang="ts">
    import Upload from "./lib/components/Upload.svelte"
    import DocumentList from "./lib/components/DocumentList.svelte"
    import TopControls from "./lib/components/TopControls.svelte"
    import LifeguardHelp from "./lib/components/LifeguardHelp.svelte"
    import { onMount } from "svelte"

    type ThemeMode = "system" | "light" | "dark"

    let refreshKey = 0
    let themeMode: ThemeMode = "system"
    let language: "en" | "ru" = "en"

    const labels = {
        en: {
            title: "OCR System"
        },
        ru: {
            title: "OCR Система"
        }
    }

    function handleUpload() {
        refreshKey += 1
    }

    function applyTheme(mode: ThemeMode) {
        themeMode = mode

        if (mode === "system") {
            document.body.removeAttribute("data-theme")
        } else {
            document.body.setAttribute("data-theme", mode)
        }

        localStorage.setItem("themeMode", mode)
    }

    function setLanguage(newLanguage: "en" | "ru") {
        language = newLanguage
        localStorage.setItem("language", newLanguage)
        document.documentElement.lang = newLanguage
    }

    onMount(() => {
        const savedTheme = (localStorage.getItem("themeMode") as ThemeMode | null) ?? "system"
        const savedLanguage = (localStorage.getItem("language") as "en" | "ru" | null) ?? "en"

        applyTheme(savedTheme)
        setLanguage(savedLanguage)
    })
</script>

<TopControls
    mode={themeMode}
    {language}
    onThemeChange={applyTheme}
    onLanguageChange={setLanguage}
/>

<h2>{labels[language].title}</h2>

<Upload on:uploaded={handleUpload} />

<DocumentList {refreshKey} />

<LifeguardHelp />
