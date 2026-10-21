import { postJson, request, saveToken } from './api'

export type User = {
  id: number
  email: string
}

export const getMe = () => request<User>('/auth/me')

export const register = (email: string, password: string) => postJson<User>('/auth/register', { email, password })

// /auth/login suit le standard OAuth2 : formulaire avec `username` (ici l'e-mail) et `password`.
export async function login(email: string, password: string) {
  const { access_token } = await request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: email, password }),
  })
  saveToken(access_token)
}
