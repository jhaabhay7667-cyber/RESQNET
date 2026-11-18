import type {
  AlgorithmTrace,
  Ambulance,
  DashboardData,
  Emergency,
  Hospital,
  RouteResult,
  User,
} from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiRequestError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('resqnet.access')
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null
    throw new ApiRequestError(body?.detail ?? `Request failed (${response.status})`, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  request,
  auth: {
    login: (username: string, password: string) =>
      request<{ access_token: string; refresh_token: string; user: User }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }),
    register: (data: { username: string; email: string; password: string; role: User['role'] | string }) => {
      const normalizedRole = String(data.role ?? '').trim()
      const aliases: Record<string, User['role']> = {
        admin: 'Administrator',
        administrator: 'Administrator',
        dispatcher: 'Emergency Dispatcher',
        'emergency dispatcher': 'Emergency Dispatcher',
        field: 'Field Operator',
        'field operator': 'Field Operator',
        hospital: 'Hospital Operator',
        'hospital operator': 'Hospital Operator',
      }
      return request<{ access_token: string; refresh_token: string; user: User }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ ...data, role: aliases[normalizedRole.toLowerCase()] ?? normalizedRole }),
      })
    },
    me: () => request<{ user: User }>('/auth/me'),
    logout: (refresh_token: string) => request<{ ok: boolean }>('/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token }) }),
  },
  dashboard: () => request<DashboardData>('/analytics/dashboard'),
  emergencies: {
    list: () => request<Emergency[]>('/emergencies'),
    create: (data: Record<string, unknown>) => request<Emergency>('/emergencies', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, unknown>) => request<Emergency>(`/emergencies/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  ambulances: {
    list: () => request<Ambulance[]>('/ambulances'),
    create: (data: Record<string, unknown>) => request<Ambulance>('/ambulances', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, unknown>) => request<Ambulance>(`/ambulances/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    location: (id: string, latitude: number, longitude: number) => request<Ambulance>(`/ambulances/${id}/location`, { method: 'PATCH', body: JSON.stringify({ latitude, longitude }) }),
  },
  hospitals: {
    list: () => request<Hospital[]>('/hospitals'),
    create: (data: Record<string, unknown>) => request<Hospital>('/hospitals', { method: 'POST', body: JSON.stringify(data) }),
    recommend: (latitude: number, longitude: number) =>
      request<Hospital[]>(`/hospitals/recommend?latitude=${latitude}&longitude=${longitude}`),
  },
  dispatch: {
    list: () => request<Array<Record<string, unknown>>>('/dispatch'),
    recommend: (emergencyId: string) => request<Record<string, unknown>>(`/dispatch/recommend/${emergencyId}`),
    approve: (emergencyId: string, vehicleId: string) =>
      request<Record<string, unknown>>(`/dispatch/${emergencyId}/approve`, { method: 'POST', body: JSON.stringify({ vehicle_id: vehicleId }) }),
  },
  routing: {
    calculate: (data: Record<string, unknown>) => request<RouteResult>('/routing/route', { method: 'POST', body: JSON.stringify(data) }),
  },
  dsa: {
    run: (data: Record<string, unknown>) => request<AlgorithmTrace>('/dsa/run', { method: 'POST', body: JSON.stringify(data) }),
  },
  publicSos: {
    create: (data: Record<string, unknown>) => request<{ id: string; status: string; created_at: string; cancel_token: string }>('/public/sos', { method: 'POST', body: JSON.stringify(data) }),
    track: (id: string) => request<Emergency>(`/public/sos/${id}`),
    cancel: (id: string) => {
      const key = `resqnet.sos.cancel.${id}`
      const cancel_token = localStorage.getItem(key)
      if (!cancel_token) throw new Error('Cancellation token is unavailable in this browser')
      return request<Emergency>(`/public/sos/${id}/cancel`, { method: 'POST', body: JSON.stringify({ cancel_token }) }).then((result) => {
        localStorage.removeItem(key)
        return result
      })
    },
  },
}

export function saveSession(data: { access_token: string; refresh_token: string; user: User }) {
  localStorage.setItem('resqnet.access', data.access_token)
  localStorage.setItem('resqnet.refresh', data.refresh_token)
  localStorage.setItem('resqnet.user', JSON.stringify(data.user))
}

export function clearSession() {
  localStorage.removeItem('resqnet.access')
  localStorage.removeItem('resqnet.refresh')
  localStorage.removeItem('resqnet.user')
}

export function readSessionUser(): User | null {
  try {
    const value = localStorage.getItem('resqnet.user')
    return value ? JSON.parse(value) as User : null
  } catch {
    return null
  }
}
