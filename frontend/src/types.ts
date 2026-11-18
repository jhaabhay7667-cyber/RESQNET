export type Role = 'Administrator' | 'Emergency Dispatcher' | 'Field Operator' | 'Hospital Operator'
export type Severity = 'Critical' | 'High' | 'Medium' | 'Low'
export type EmergencyStatus = 'Open' | 'Pending Approval' | 'Dispatched' | 'En Route' | 'On Scene' | 'Transporting' | 'Resolved' | 'Cancelled'
export type VehicleStatus = 'Available' | 'Dispatched' | 'En Route' | 'On Scene' | 'Transporting' | 'Out of Service'

export interface User {
  id: string
  username: string
  email: string
  role: Role
}

export interface Emergency {
  id: string
  title: string
  category: string
  severity: Severity
  priority: number
  latitude: number
  longitude: number
  description: string
  status: EmergencyStatus
  assigned_vehicle_id?: string | null
  created_at: string
}

export interface Ambulance {
  id: string
  name: string
  vehicle_type: string
  status: VehicleStatus
  latitude: number
  longitude: number
  capacity: number
  equipment: string
  last_updated?: string
}

export interface Hospital {
  id: string
  name: string
  latitude: number
  longitude: number
  available_beds: number
  icu_capacity: number
  emergency_facilities: string
  accepting_patients?: boolean
}

export interface DashboardData {
  stats: {
    activeEmergencies: number
    criticalIncidents: number
    availableAmbulances: number
    dispatchedVehicles: number
    hospitalsAvailable: number
    averageResponseTime: number
  }
  activity: Array<{ id: string; message: string; time: string; type: string }>
  distribution: Array<{ name: string; value: number }>
  utilization: Array<{ name: string; value: number }>
}

export interface RouteResult {
  algorithm: string
  path: string[]
  distance: number
  travel_cost: number
  nodes_explored: number
  execution_time_ms: number
  alternative_path?: string[]
  coordinates?: [number, number][]
  blocked_roads?: Array<{ start: string; end: string; coordinates?: [number, number][] }>
  estimated_travel_time_min?: number
}

export interface AlgorithmTrace {
  algorithm: string
  path: string[]
  distance: number
  nodes_explored: number
  execution_time_ms: number
  time_complexity: string
  space_complexity: string
  trace: Array<{ step: number; node: string; state: 'current' | 'visited' | 'path'; distance?: number }>
}

export interface ApiError extends Error {
  status?: number
}
