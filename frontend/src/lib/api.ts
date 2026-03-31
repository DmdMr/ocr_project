// api.ts
//const BACKEND_HOST = window.location.hostname; // automatically matches localhost or LAN IP
//const API_URL = `http://${BACKEND_HOST}:8000/api`;
//console.log(BACKEND_HOST);

//const API_URL = "http://192.168.31.162:8000/api"; // your Mac’s LAN IP

export const API_URL = "/api"; // Use your LAN IP

//export const API_URL = `http://${window.location.hostname}:8000/api`

console.log(API_URL);

//export const UPLOADS_URL = "http://localhost:8000/uploads";

export const UPLOADS_URL = "/uploads"

console.log(UPLOADS_URL);

async function apiFetch(url: string, init: RequestInit = {}) {
    return fetch(url, {
        credentials: "include",
        ...init
    })
}

export interface AppSettingsResponse {
    fields_for_cards: Array<{ name: string; type: "text" | "number"; created_at?: string }>
}

export async function uploadImage(file: File, performOcr = true) {
    const formData = new FormData()
    formData.append("file", file)
    formData.append("perform_ocr", String(performOcr))

    const res = await apiFetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData
    })

    if (!res.ok) {
        throw new Error("Failed to upload image")
    }

    return await res.json()
}

export async function uploadImagesToDocument(documentId: string, files: File[]) {
    const formData = new FormData()
    for (const file of files) {
        formData.append("files", file)
    }

    const res = await apiFetch(`${API_URL}/documents/${documentId}/gallery`, {
        method: "POST",
        body: formData
    })

    const data = await res.json().catch(() => ({}))

    if (!res.ok) {
        throw new Error(data.detail || "Failed to upload images to card")
    }

    return data
}

export async function uploadDocumentAttachments(documentId: string, files: File[]) {
    const formData = new FormData()
    for (const file of files) {
        formData.append("files", file)
    }

    const response = await apiFetch(`${API_URL}/documents/${documentId}/attachments`, {
        method: "POST",
        body: formData
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(data.detail || "Failed to upload files to card")
    }

    return data
}

export async function getDocumentById(id: string) {
    const res = await apiFetch(`${API_URL}/documents/${id}`)
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || "Failed to fetch document")
    return data
}

export async function getDocuments() {
    const res = await apiFetch(`${API_URL}/documents`)
    if (!res.ok) throw new Error("Failed to fetch documents")
    return await res.json()
}

export async function deleteDocument(id: string) {
    const res = await apiFetch(`${API_URL}/documents/${id}`, {
        method: "DELETE"
    })

    if (!res.ok) throw new Error("Failed to delete document")
    return await res.json().catch(() => ({}))
}

export async function getArchivedDocuments() {
    const res = await apiFetch(`${API_URL}/documents/archived`)
    if (!res.ok) throw new Error("Failed to fetch archived documents")
    return await res.json()
}

export async function restoreArchivedDocument(id: string) {
    const res = await apiFetch(`${API_URL}/documents/${id}/restore`, {
        method: "POST"
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || "Failed to restore document")
    return data
}

export async function permanentlyDeleteArchivedDocument(id: string) {
    const res = await apiFetch(`${API_URL}/documents/${id}/permanent`, {
        method: "DELETE"
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || "Failed to permanently delete document")
    return data
}

export async function bulkRestoreArchivedDocuments(ids: string[]) {
    const res = await apiFetch(`${API_URL}/documents/archive/restore-bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids })
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || "Failed to restore documents")
    return data
}

export async function bulkPermanentlyDeleteArchivedDocuments(ids: string[]) {
    const res = await apiFetch(`${API_URL}/documents/archive/permanent-delete-bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids })
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || "Failed to permanently delete documents")
    return data
}

export async function updateDocument(id: string, data: any) {
    const response = await apiFetch(`${API_URL}/documents/${id}`, {
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

export async function getSettings() {
    const response = await apiFetch(`${API_URL}/settings`)
    const data: AppSettingsResponse = await response.json().catch(() => ({ fields_for_cards: [] }))
    if (!response.ok) {
        throw new Error("Failed to fetch settings")
    }
    return data
}

export async function createCardField(name: string, type: "text" | "number") {
    const response = await apiFetch(`${API_URL}/settings/fields`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, type })
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
        throw new Error(data.detail || "Failed to create field")
    }
    return data
}

export async function deleteCardField(name: string) {
    const response = await apiFetch(`${API_URL}/settings/fields/${encodeURIComponent(name)}`, {
        method: "DELETE"
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
        throw new Error(data.detail || "Failed to delete field")
    }
    return data
}

export async function updateDocumentCustomFields(id: string, customFields: Record<string, string | number | null>) {
    const response = await apiFetch(`${API_URL}/documents/${id}/fields`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ custom_fields: customFields })
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
        throw new Error(data.detail || "Failed to update custom fields")
    }
    return data
}


export async function setDocumentTags(id: string, tags: string[]) {
    return updateDocument(id, { tags })
}

export async function searchDocuments(q: string) {
    const res = await apiFetch(`${API_URL}/search?q=${encodeURIComponent(q)}`)
    if (!res.ok) throw new Error("Search request failed")
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
    const response = await apiFetch(`${API_URL}/tags`)
    if (!response.ok) {
        throw new Error("Failed to fetch tags")
    }

    const data = await response.json()
    return data.tags ?? []
}


export async function createTag(tag: string) {
    const response = await apiFetch(`${API_URL}/tags`, {
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
    const response = await apiFetch(`${API_URL}/tags/${encodeURIComponent(normalizeTag(tag))}`, {
        method: "DELETE"
    })

    const payload = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(payload.detail || "Failed to delete tag")
    }

    return payload
}



export interface ImageEditPayload {
    rotate_degrees?: number
    image_filename?: string
    crop?: {
        x_percent: number
        y_percent: number
        width_percent: number
        height_percent: number
    }
}

export async function editDocumentImage(id: string, payload: ImageEditPayload) {
    const response = await apiFetch(`${API_URL}/documents/${id}/image`, {
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

export async function deleteDocumentAttachment(id: string, attachmentFilename: string) {
    const response = await apiFetch(`${API_URL}/documents/${id}/attachments/${encodeURIComponent(attachmentFilename)}`, {
        method: "DELETE"
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(data.detail || "Failed to delete attachment")
    }

    return data
}

export async function deleteDocumentImage(id: string, imageFilename: string) {
    const response = await apiFetch(`${API_URL}/documents/${id}/gallery/${encodeURIComponent(imageFilename)}`, {
        method: "DELETE"
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(data.detail || "Failed to delete image")
    }

    return data
}


export interface AuthUser {
    id: string
    username: string
    created_at?: string
    is_active?: boolean
}

export async function register(username: string, password: string): Promise<AuthUser> {
    const response = await apiFetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || "Failed to register")
    return data
}

export async function login(username: string, password: string): Promise<AuthUser> {
    const response = await apiFetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || "Failed to login")
    return data
}

export async function logout() {
    const response = await apiFetch(`${API_URL}/auth/logout`, { method: "POST" })
    if (!response.ok) throw new Error("Failed to logout")
}

export async function getCurrentUser(): Promise<AuthUser | null> {
    const response = await apiFetch(`${API_URL}/auth/me`)
    if (response.status === 401) return null
    const data = await response.json().catch(() => null)
    if (!response.ok) throw new Error("Failed to load current user")
    return data
}
