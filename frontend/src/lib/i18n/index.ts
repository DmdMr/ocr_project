import { derived, writable } from "svelte/store"
import en from "./en"
import ru from "./ru"

export type Language = "en" | "ru"
export type TranslationKey = keyof typeof en

type Dictionary = Record<string, string>

const dictionaries: Record<Language, Dictionary> = { en, ru }
const STORAGE_KEY = "language"

function detectDefaultLanguage(): Language {
  if (typeof localStorage !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === "en" || stored === "ru") return stored
  }

  if (typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("ru")) {
    return "ru"
  }

  return "en"
}

function format(template: string, params?: Record<string, string | number>) {
  if (!params) return template
  return template.replace(/\{(\w+)\}/g, (_, key) => String(params[key] ?? `{${key}}`))
}

export const language = writable<Language>(detectDefaultLanguage())

language.subscribe((value) => {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, value)
  }
  if (typeof document !== "undefined") {
    document.documentElement.lang = value
  }
})

export const t = derived(language, ($language) => {
  return (key: TranslationKey | string, params?: Record<string, string | number>) => {
    const current = dictionaries[$language][key]
    const fallback = dictionaries.en[key]
    return format(current ?? fallback ?? key, params)
  }
})

export function setLanguage(nextLanguage: Language) {
  language.set(nextLanguage)
}

export function getLanguageName(value: Language) {
  return value === "ru" ? "Русский" : "English"
}
