import type { Document } from "./types"

export function slugifyDocumentName(name: string) {
  const base = (name || "").trim().toLowerCase()
  if (!base) return "document"

  return base
    .replace(/\.[a-z0-9]{1,8}$/i, "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "document"
}

export function documentSlug(doc: Pick<Document, "display_filename" | "filename">) {
  return slugifyDocumentName(doc.display_filename || doc.filename || "document")
}

export function documentRouteById(id: string, slug?: string | null) {
  const normalizedSlug = (slug || "").trim()
  return normalizedSlug ? `/document/${id}/${encodeURIComponent(normalizedSlug)}` : `/document/${id}`
}

export function documentRoute(doc: Pick<Document, "_id" | "display_filename" | "filename">) {
  return documentRouteById(doc._id, documentSlug(doc))
}
