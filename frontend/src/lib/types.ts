export interface Document {
    _id: string
    filename: string
    recognized_text: string
    created_at: string
    tags?: string[]   
}