import { fetchAuthSession } from 'aws-amplify/auth'

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT

async function authHeaders() {
  const session = await fetchAuthSession()
  const token = session.tokens.idToken.toString()
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }
}

async function request(path, options = {}) {
  const headers = await authHeaders()
  const res = await fetch(`${API_ENDPOINT}${path}`, { ...options, headers })
  if (res.status === 204) return null
  const data = await res.json()
  if (!res.ok) throw new Error(data.message || 'Request failed')
  return data
}

export const listTasks = () => request('/tasks')

export const createTask = (payload) =>
  request('/tasks', { method: 'POST', body: JSON.stringify(payload) })

export const getTask = (taskId) => request(`/tasks/${taskId}`)

export const updateTask = (taskId, payload) =>
  request(`/tasks/${taskId}`, { method: 'PUT', body: JSON.stringify(payload) })

export const deleteTask = (taskId) =>
  request(`/tasks/${taskId}`, { method: 'DELETE' })
