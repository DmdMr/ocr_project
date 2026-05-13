// api.ts
import { get } from "svelte/store"
import { t } from "./i18n"
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

export type ApiErrorCode =
    | "OCR_FAILURE"
    | "INVALID_IMAGE"
    | "FILE_TOO_LARGE"
    | "NETWORK_ERROR"
    | "AUTH_REQUIRED"
    | "INVALID_CREDENTIALS"
    | "ACCESS_DENIED"
    | "VALIDATION_ERROR"
    | "NOT_FOUND"
    | "BAD_REQUEST"
    | "DUPLICATE_FILE"
    | "INTERNAL_ERROR"

export interface SkippedFileError {
    filename?: string
    error_code?: ApiErrorCode
}

export class ApiError extends Error {
    errorCode: ApiErrorCode
    status?: number

    constructor(errorCode: ApiErrorCode, status?: number) {
        super(translateApiError(errorCode))
        this.name = "ApiError"
        this.errorCode = errorCode
        this.status = status
    }
}

function translateApiError(errorCode: ApiErrorCode) {
    return get(t)(`errors.${errorCode}`)
}

function fallbackErrorCode(status?: number): ApiErrorCode {
    if (status === 401) return "AUTH_REQUIRED"
    if (status === 403) return "ACCESS_DENIED"
    if (status === 404) return "NOT_FOUND"
    if (status === 413) return "FILE_TOO_LARGE"
    if (status === 422) return "VALIDATION_ERROR"
    if (status && status >= 500) return "INTERNAL_ERROR"
    return "BAD_REQUEST"
}

export function formatSkippedFileError(item: SkippedFileError | string) {
    if (typeof item === "string") return get(t)("errors.BAD_REQUEST")
    const filename = item.filename?.trim()
    const errorCode = item.error_code && get(t)(`errors.${item.error_code}`) !== `errors.${item.error_code}`
        ? item.error_code
        : "BAD_REQUEST"
    const message = translateApiError(errorCode)
    return filename ? `${filename}: ${message}` : message
}

function parseApiErrorCode(payload: any, status?: number): ApiErrorCode {
    const detail = payload?.detail
    const errorCode = payload?.error_code ?? (typeof detail === "object" ? detail?.error_code : undefined)
    if (typeof errorCode === "string" && get(t)(`errors.${errorCode}`) !== `errors.${errorCode}`) {
        return errorCode as ApiErrorCode
    }
    return fallbackErrorCode(status)
}

async function parseJson(response: Response) {
    return await response.json().catch(() => ({}))
}

async function parseJsonOrThrow(response: Response) {
    const data = await parseJson(response)
    if (!response.ok) {
        throw new ApiError(parseApiErrorCode(data, response.status), response.status)
    }
    return data
}

async function apiFetch(url: string, init: RequestInit = {}) {
    try {
        return await fetch(url, {
            credentials: "include",
            ...init
        })
    } catch (error) {
        throw new ApiError("NETWORK_ERROR")
    }
}

export interface CardFieldDefinition {
    name: string
    type: "text" | "number" | "people"
}

export interface AppSettingsResponse {
    fields_for_cards: CardFieldDefinition[]
}

export async function uploadImage(file: File, performOcr = true) {
    const formData = new FormData()
    formData.append("file", file)
    formData.append("perform_ocr", String(performOcr))

    const res = await apiFetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData
    })

    return await parseJsonOrThrow(res)
}

export async function uploadImagesToDocument(
    documentId: string,
    files: File[],
    onProgress?: (percent: number) => void,
    performOcr = true
) {
    const formData = new FormData()
    for (const file of files) {
        formData.append("files", file)
    }
    formData.append("perform_ocr", String(performOcr))

    return await uploadFormWithProgress(`${API_URL}/documents/${documentId}/gallery`, formData, onProgress)
}

export async function uploadDocumentAttachments(
    documentId: string,
    files: File[],
    onProgress?: (percent: number) => void
) {
    const formData = new FormData()
    for (const file of files) {
        formData.append("files", file)
    }

    return await uploadFormWithProgress(`${API_URL}/documents/${documentId}/attachments`, formData, onProgress)
}

async function uploadFormWithProgress(
    url: string,
    formData: FormData,
    onProgress?: (percent: number) => void
) {
    if (!onProgress) {
        const response = await apiFetch(url, { method: "POST", body: formData })
        return await parseJsonOrThrow(response)
    }

    return await new Promise<any>((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        xhr.open("POST", url, true)
        xhr.withCredentials = true

        xhr.upload.onprogress = (event) => {
            if (!event.lengthComputable) return
            onProgress(Math.round((event.loaded / event.total) * 100))
        }

        xhr.onload = () => {
            const raw = xhr.responseText || "{}"
            const data = (() => {
                try {
                    return JSON.parse(raw)
                } catch {
                    return {}
                }
            })()
            if (xhr.status >= 200 && xhr.status < 300) {
                onProgress(100)
                resolve(data)
                return
            }
            reject(new ApiError(parseApiErrorCode(data, xhr.status), xhr.status))
        }

        xhr.onerror = () => reject(new ApiError("NETWORK_ERROR"))
        xhr.send(formData)
    })
}

export async function getDocuments() {
    const res = await apiFetch(`${API_URL}/documents`)
    return await parseJsonOrThrow(res)
}

export async function getDocumentById(id: string) {
    const res = await apiFetch(`${API_URL}/documents/${encodeURIComponent(id)}`)
    return await parseJsonOrThrow(res)
}

export async function getFolderTree() {
    const res = await apiFetch(`${API_URL}/folders/tree`)
    return await parseJsonOrThrow(res)
}

export async function getFolderContents(folderId: string) {
    const res = await apiFetch(`${API_URL}/folders/${encodeURIComponent(folderId)}/contents`)
    return await parseJsonOrThrow(res)
}

export async function createFolder(name: string, parentId?: string | null) {
    const res = await apiFetch(`${API_URL}/folders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, parent_id: parentId ?? null })
    })
    return await parseJsonOrThrow(res)
}

export async function renameFolder(folderId: string, name: string) {
    const res = await apiFetch(`${API_URL}/folders/${encodeURIComponent(folderId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
    })
    return await parseJsonOrThrow(res)
}

export async function deleteFolderById(folderId: string) {
    const res = await apiFetch(`${API_URL}/folders/${encodeURIComponent(folderId)}`, { method: "DELETE" })
    return await parseJsonOrThrow(res)
}

export async function moveFolder(folderId: string, targetParentId?: string | null) {
    const res = await apiFetch(`${API_URL}/folders/${encodeURIComponent(folderId)}/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_parent_id: targetParentId ?? null })
    })
    return await parseJsonOrThrow(res)
}

export async function moveDocumentToFolder(documentId: string, targetFolderId: string) {
    const res = await apiFetch(`${API_URL}/documents/${encodeURIComponent(documentId)}/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_folder_id: targetFolderId })
    })
    return await parseJsonOrThrow(res)
}

export async function getFolderPath(folderId: string) {
    const res = await apiFetch(`${API_URL}/folders/${encodeURIComponent(folderId)}/path`)
    return await parseJsonOrThrow(res)
}

export async function getDocumentPath(documentId: string) {
    const res = await apiFetch(`${API_URL}/documents/${encodeURIComponent(documentId)}/path`)
    return await parseJsonOrThrow(res)
}

export async function deleteDocument(id: string) {
    const res = await apiFetch(`${API_URL}/documents/${id}`, {
        method: "DELETE"
    })

    return await parseJsonOrThrow(res)
}

export async function getArchivedDocuments() {
    const res = await apiFetch(`${API_URL}/documents/archived`)
    return await parseJsonOrThrow(res)
}

export async function restoreArchivedDocument(id: string) {
    const res = await apiFetch(`${API_URL}/documents/${id}/restore`, {
        method: "POST"
    })
    return await parseJsonOrThrow(res)
}

export async function permanentlyDeleteArchivedDocument(id: string) {
    const res = await apiFetch(`${API_URL}/documents/${id}/permanent`, {
        method: "DELETE"
    })
    return await parseJsonOrThrow(res)
}

export async function bulkRestoreArchivedDocuments(ids: string[]) {
    const res = await apiFetch(`${API_URL}/documents/archive/restore-bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids })
    })
    return await parseJsonOrThrow(res)
}

export async function bulkPermanentlyDeleteArchivedDocuments(ids: string[]) {
    const res = await apiFetch(`${API_URL}/documents/archive/permanent-delete-bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids })
    })
    return await parseJsonOrThrow(res)
}

export async function updateDocument(id: string, data: any) {
    const response = await apiFetch(`${API_URL}/documents/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })

    return await parseJsonOrThrow(response)
}

export async function getCardFields() {
    const response = await apiFetch(`${API_URL}/settings/fields`)
    return (await parseJsonOrThrow(response)) as CardFieldDefinition[]
}

export async function getSettings() {
    const fields = await getCardFields()
    return { fields_for_cards: fields }
}

export async function createCardField(name: string, type: "text" | "number" | "people") {
    const response = await apiFetch(`${API_URL}/settings/fields`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, type })
    })
    return await parseJsonOrThrow(response)
}

export async function deleteCardField(name: string) {
    const response = await apiFetch(`${API_URL}/settings/fields/${encodeURIComponent(name)}`, {
        method: "DELETE"
    })
    return await parseJsonOrThrow(response)
}

export async function updateDocumentCustomFields(id: string, customFields: Record<string, string | number | string[] | null>) {
    const response = await apiFetch(`${API_URL}/documents/${id}/fields`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ custom_fields: customFields })
    })
    return await parseJsonOrThrow(response)
}


export async function setDocumentTags(id: string, tags: string[]) {
    return updateDocument(id, { tags })
}

export async function searchDocuments(q: string) {
    const res = await apiFetch(`${API_URL}/search?q=${encodeURIComponent(q)}`)
    return await parseJsonOrThrow(res)
}

export function normalizeTag(tag: string) {
    return tag.trim().toLowerCase().replace(/\s+/g, " ")
}

export function isValidTagName(tag: string) {
    const normalized = normalizeTag(tag)
    return normalized.length > 0 && normalized.length <= 64 && /^[\p{L}\p{N}_ .-]+$/u.test(normalized)
}

export function tagExists(tags: string[], tag: string) {
    const normalized = normalizeTag(tag)
    return tags.some(existing => normalizeTag(existing) === normalized)
}

export async function getTags(): Promise<string[]> {
    const response = await apiFetch(`${API_URL}/tags`)
    const data = await parseJsonOrThrow(response)
    return data.tags ?? []
}



export interface SystemNetworkInfo {
    local_ip: string
    port: number
    url: string
    status?: string
}

export async function getSystemNetwork(): Promise<SystemNetworkInfo> {
    const response = await apiFetch(`${API_URL}/system/network`)
    return await parseJsonOrThrow(response)
}

export async function createTag(tag: string) {
    const response = await apiFetch(`${API_URL}/tags`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ tag })
    })

    return await parseJsonOrThrow(response)
}

export async function deleteTag(tag: string) {
    const response = await apiFetch(`${API_URL}/tags/${encodeURIComponent(normalizeTag(tag))}`, {
        method: "DELETE"
    })

    return await parseJsonOrThrow(response)
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

    return await parseJsonOrThrow(response)
}

export async function deleteDocumentAttachment(id: string, attachmentFilename: string) {
    const response = await apiFetch(`${API_URL}/documents/${id}/attachments/${encodeURIComponent(attachmentFilename)}`, {
        method: "DELETE"
    })

    return await parseJsonOrThrow(response)
}

export async function deleteDocumentImage(id: string, imageFilename: string) {
    const response = await apiFetch(`${API_URL}/documents/${id}/gallery/${encodeURIComponent(imageFilename)}`, {
        method: "DELETE"
    })

    return await parseJsonOrThrow(response)
}


export interface AuthUser {
    id: string | null
    username: string | null
    role: "viewer" | "editor" | "admin"
    is_authenticated?: boolean
    created_at?: string
    updated_at?: string
    is_active?: boolean
}

export async function register(username: string, password: string): Promise<AuthUser> {
    const response = await apiFetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    })
    return await parseJsonOrThrow(response)
}

export async function login(username: string, password: string): Promise<AuthUser> {
    const response = await apiFetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    })
    return await parseJsonOrThrow(response)
}

export async function logout() {
    const response = await apiFetch(`${API_URL}/auth/logout`, { method: "POST" })
    if (!response.ok) await parseJsonOrThrow(response)
}

export async function getCurrentUser(): Promise<AuthUser | null> {
    const response = await apiFetch(`${API_URL}/auth/me`)
    if (response.status === 401) return null
    return await parseJsonOrThrow(response)
}

export interface AdminUserPayload {
    username: string
    password: string
    role: "editor" | "admin"
    is_active: boolean
}

export interface AdminUserUpdatePayload {
    username?: string
    role?: "editor" | "admin"
    is_active?: boolean
}

export interface ActivityLogEntry {
    id: string
    timestamp?: string
    created_at?: string
    action: string
    actor: Record<string, unknown>
    payload: Record<string, unknown>
}

export async function getUsers(): Promise<AuthUser[]> {
    const response = await apiFetch(`${API_URL}/users`)
    const data = await parseJsonOrThrow(response)
    return data.users ?? []
}

export async function createUserByAdmin(payload: AdminUserPayload): Promise<AuthUser> {
    const response = await apiFetch(`${API_URL}/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    return await parseJsonOrThrow(response)
}

export async function updateUserByAdmin(userId: string, payload: AdminUserUpdatePayload): Promise<AuthUser> {
    const response = await apiFetch(`${API_URL}/users/${encodeURIComponent(userId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    return await parseJsonOrThrow(response)
}

export async function resetUserPasswordByAdmin(userId: string, newPassword: string) {
    const response = await apiFetch(`${API_URL}/users/${encodeURIComponent(userId)}/password`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_password: newPassword })
    })
    return await parseJsonOrThrow(response)
}

export async function getActivityLogs(limit = 100): Promise<ActivityLogEntry[]> {
    const response = await apiFetch(`${API_URL}/activity-logs?limit=${encodeURIComponent(String(limit))}`)
    const data = await parseJsonOrThrow(response)
    return data.logs ?? []
}
