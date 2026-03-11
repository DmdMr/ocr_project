const resolvedHostname = typeof window !== "undefined" ? window.location.hostname : "localhost"
const apiHost = import.meta.env.VITE_API_HOST || resolvedHostname
const apiPort = import.meta.env.VITE_API_PORT || "8000"

export const API_URL =
  import.meta.env.VITE_API_URL ||
  `http://${apiHost}:${apiPort}/api`

export const UPLOADS_URL =
  import.meta.env.VITE_UPLOADS_URL ||
  `http://${apiHost}:${apiPort}/uploads`

export async function uploadImage(file: File) {
    const formData = new FormData()
    formData.append("file", file)

    const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData
    })

    return await res.json()
}

export async function getDocuments() {
    const res = await fetch(`${API_URL}/documents`)
    return await res.json()
}

export async function deleteDocument(id: string) {
    await fetch(`${API_URL}/documents/${id}`, {
        method: "DELETE"
    })
}

export async function updateDocument(id: string, data: any) {
    const response = await fetch(`${API_URL}/documents/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })

    if (!response.ok) {
        throw new Error("Failed to update document")
    }

    return response.json()
}

export async function setDocumentTags(id: string, tags: string[]) {
    return updateDocument(id, { tags })
}


export interface ImageEditPayload {
    rotate_degrees?: number
    crop?: {
        x_percent: number
        y_percent: number
        width_percent: number
        height_percent: number
    }
}

export async function editDocumentImage(id: string, payload: ImageEditPayload) {
    const response = await fetch(`${API_URL}/documents/${id}/image`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(data.detail || "Failed to edit image")
    }

    return data
}

export async function searchDocuments(q: string) {
    const res = await fetch(`${API_URL}/search?q=${q}`)
    return await res.json()
}

export function normalizeTag(tag: string) {
    return tag.trim().toLowerCase()
}

export function tagExists(tags: string[], tag: string) {
    const normalized = normalizeTag(tag)
    return tags.some(existing => normalizeTag(existing) === normalized)
}

export async function getTags(): Promise<string[]> {
    const response = await fetch(`${API_URL}/tags`)
    if (!response.ok) {
        throw new Error("Failed to fetch tags")
    }

    const data = await response.json()
    return data.tags ?? []
}

export async function createTag(tag: string) {
    const response = await fetch(`${API_URL}/tags`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ tag })
    })

    const payload = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(payload.detail || "Failed to create tag")
    }

    return payload
}

export async function deleteTag(tag: string) {
    const response = await fetch(`${API_URL}/tags/${encodeURIComponent(normalizeTag(tag))}`, {
        method: "DELETE"
    })

    const payload = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(payload.detail || "Failed to delete tag")
    }

    return payload
}
