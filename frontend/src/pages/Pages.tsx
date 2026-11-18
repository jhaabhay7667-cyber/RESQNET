import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Activity, Ambulance as AmbulanceIcon, ArrowRight, BarChart3, BedDouble, BrainCircuit, Clock3,
  Crosshair, Hospital, MapPin, Navigation, Plus, Route, ShieldAlert, Siren, Stethoscope, XCircle,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { AlgorithmTrace, Ambulance, DashboardData, Emergency, Hospital as HospitalType, RouteResult } from '../types'
import {
  Button, Card, ConfirmDialog, EmptyState, Field, PageTitle, SelectField, Skeleton, StatusChip,
  TextAreaField, useToast,
} from '../components/Ui'

const mapCenter: [number, number] = [40.73, -74.0]
const chartTooltip = { contentStyle: { background: '#0f172a', border: '1px solid #334155', borderRadius: 12, color: '#e2e8f0' } }
const chartGrid = '#253247'

function usePageLoad<T>(loader: () => Promise<T>, initial: T) {
  const [data, setData] = useState(initial)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setData(await loader()) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to load data') }
    finally { setLoading(false) }
  }, [loader])
  useEffect(() => { void refresh() }, [refresh])
  return { data, setData, loading, error, refresh }
}

function ErrorMessage({ children }: { children: ReactNode }) {
  return <div role="alert" className="mb-4 rounded-xl border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">{children}</div>
}

function Metric({ label, value, note, icon: Icon, tone = 'cyan' }: { label: string; value: string | number; note: string; icon: typeof Activity; tone?: 'cyan' | 'red' | 'green' | 'amber' }) {
  const tones = { cyan: 'bg-cyan-400/10 text-cyan-300', red: 'bg-red-400/10 text-red-300', green: 'bg-emerald-400/10 text-emerald-300', amber: 'bg-amber-400/10 text-amber-200' }
  return <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rounded-2xl border border-slate-800 bg-[#111827]/90 p-5"><div className="flex items-start justify-between"><div><p className="text-sm text-slate-400">{label}</p><div className="mt-2 text-3xl font-semibold text-white">{value}</div></div><div className={`rounded-xl p-2.5 ${tones[tone]}`}><Icon size={18} /></div></div><div className="mt-3 text-xs text-slate-500">{note}</div></motion.div>
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#080d18] text-slate-100">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5"><Link to="/" className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400 text-slate-950"><ShieldAlert size={20} /></span><span className="font-bold tracking-[0.16em] text-white">RESQNET</span></Link><nav className="flex items-center gap-2"><Link to="/sos" className="hidden rounded-xl px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 sm:block">Public SOS</Link><Link to="/login" className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800">Sign in</Link><Link to="/register" className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300">Create account</Link></nav></header>
      <main className="mx-auto grid max-w-7xl gap-12 px-5 pb-20 pt-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pt-20">
        <div><StatusChip tone="amber">SIMULATION PLATFORM · NOT AN EMERGENCY SERVICE</StatusChip><h1 className="mt-7 max-w-3xl text-5xl font-semibold leading-[1.08] tracking-tight text-white md:text-7xl">Every second matters.<br /><span className="text-cyan-300">Every route counts.</span></h1><p className="mt-6 max-w-2xl text-lg leading-8 text-slate-400">A coordination workspace for emergency dispatch, vehicle allocation, hospital capacity, and graph-based route planning. Built for training, evaluation, and controlled demonstrations.</p><div className="mt-8 flex flex-wrap gap-3"><Link to="/login" className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-300">Open command center <ArrowRight size={17} /></Link><Link to="/sos" className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-5 py-3 font-medium text-slate-200 hover:bg-slate-900"><Siren size={17} /> View SOS portal</Link></div><p className="mt-6 max-w-xl text-xs leading-5 text-amber-200/80">Demo only. No real emergency response, SMS, live traffic, GPS fleet tracking, or medical care is provided. For a real emergency, contact your local emergency number.</p></div>
        <Card className="relative overflow-hidden !p-0"><div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(34,211,238,.18),transparent_58%)]" /><div className="relative p-6 md:p-8"><div className="flex items-center justify-between"><div><div className="text-xs uppercase tracking-[0.2em] text-slate-500">Simulation preview</div><div className="mt-1 text-lg font-semibold text-white">Regional response overview</div></div><StatusChip tone="green">Seeded demo</StatusChip></div><div className="my-7 grid grid-cols-2 gap-3"><div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><div className="text-xs text-slate-500">Active incidents</div><div className="mt-2 text-3xl font-semibold text-white">—</div><div className="mt-1 text-xs text-slate-600">Connect to the local API</div></div><div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><div className="text-xs text-slate-500">Routes</div><div className="mt-2 text-3xl font-semibold text-cyan-300">Dijkstra · A*</div><div className="mt-1 text-xs text-slate-600">Road graph demonstrator</div></div></div><div className="grid h-56 place-items-center rounded-xl border border-slate-800 bg-slate-950/70"><div className="text-center"><MapPin className="mx-auto text-cyan-300" /><p className="mt-2 text-sm text-slate-400">Interactive map available after sign in</p><p className="mt-1 text-xs text-slate-600">OpenStreetMap tiles require an internet connection</p></div></div></div></Card>
      </main>
      <footer className="border-t border-slate-800 px-5 py-6 text-center text-xs text-slate-600">RESQNET · Controlled simulation only · Never use this app as a substitute for emergency services</footer>
    </div>
  )
}

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'Emergency Dispatcher' | 'Field Operator' | 'Hospital Operator'>('Emergency Dispatcher')
  const [error, setError] = useState('')
  const { login, register, busy } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      if (mode === 'login') await login(username.trim(), password)
      else await register({ username: username.trim(), email: email.trim(), password, role })
      notify(mode === 'login' ? 'Signed in successfully' : 'Account created', 'success')
      navigate('/app/dashboard')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Authentication failed') }
  }
  return (
    <div className="grid min-h-screen bg-[#080d18] text-slate-100 lg:grid-cols-[1.1fr_0.9fr]">
      <div className="hidden flex-col justify-between border-r border-slate-800 p-10 lg:flex"><Link to="/" className="font-bold tracking-[0.18em] text-cyan-200">RESQNET</Link><div><StatusChip tone="amber">LOCAL SIMULATION</StatusChip><h1 className="mt-6 text-5xl font-semibold leading-tight text-white">Coordinate with clarity.<br />Respond with purpose.</h1><p className="mt-5 max-w-lg text-slate-400">Secure operator access for a controlled emergency-response demonstration. Seeded information is synthetic.</p></div><p className="text-xs text-slate-600">Not a real emergency-response service.</p></div>
      <div className="flex items-center justify-center p-5"><Card className="w-full max-w-md"><Link to="/" className="text-xs text-slate-500 hover:text-cyan-200">← RESQNET home</Link><h1 className="mt-5 text-2xl font-semibold text-white">{mode === 'login' ? 'Sign in' : 'Create operator account'}</h1><p className="mt-2 text-sm text-slate-400">{mode === 'login' ? 'Enter your credentials to continue.' : 'Registration creates an account in this local demo database.'}</p>{error && <div className="mt-4"><ErrorMessage>{error}</ErrorMessage></div>}<form onSubmit={submit} className="mt-6 space-y-4"><Field label="Username" autoComplete="username" required minLength={3} value={username} onChange={(event) => setUsername(event.target.value)} />{mode === 'register' && <><Field label="Email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /><SelectField label="Role" value={role} onChange={(event) => setRole(event.target.value as typeof role)}><option>Emergency Dispatcher</option><option>Field Operator</option><option>Hospital Operator</option></SelectField></>}<Field label="Password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} /><Button type="submit" disabled={busy} className="w-full">{mode === 'login' ? 'Sign in' : 'Register'}</Button></form><p className="mt-5 text-center text-sm text-slate-500">{mode === 'login' ? 'New to RESQNET?' : 'Already registered?'} <Link className="text-cyan-300 hover:text-cyan-200" to={mode === 'login' ? '/register' : '/login'}>{mode === 'login' ? 'Create account' : 'Sign in'}</Link></p><p className="mt-5 border-t border-slate-800 pt-4 text-xs text-amber-200/80">Simulation data only. Do not enter real patient information.</p></Card></div>
    </div>
  )
}

const emptyDashboard: DashboardData = { stats: { activeEmergencies: 0, criticalIncidents: 0, availableAmbulances: 0, dispatchedVehicles: 0, hospitalsAvailable: 0, averageResponseTime: 0 }, activity: [], distribution: [], utilization: [] }

export function DashboardPage() {
  const { data: dashboard, loading, error } = usePageLoad(api.dashboard, emptyDashboard)
  const incidentsLoad = usePageLoad(api.emergencies.list, [] as Emergency[])
  const ambulancesLoad = usePageLoad(api.ambulances.list, [] as Ambulance[])
  const hospitalsLoad = usePageLoad(api.hospitals.list, [] as HospitalType[])
  const active = incidentsLoad.data.filter((incident) => !['Resolved', 'Cancelled'].includes(incident.status))
  const colors = ['#22d3ee', '#60a5fa', '#f59e0b', '#fb7185']
  return (
    <div>
      <PageTitle eyebrow="Operations overview" title="Command center" description="Operational metrics and incident activity from the local simulation database." action={<StatusChip tone="amber">Seeded simulation data</StatusChip>} />
      {error && <ErrorMessage>{error}. Start the backend to load persistent data.</ErrorMessage>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {loading ? Array.from({ length: 6 }, (_, index) => <Skeleton className="h-32" key={index} />) : <>
          <Metric label="Active emergencies" value={dashboard.stats.activeEmergencies} note="Open, pending, or in response" icon={Siren} tone="red" />
          <Metric label="Critical incidents" value={dashboard.stats.criticalIncidents} note="Highest dispatch priority" icon={ShieldAlert} tone="red" />
          <Metric label="Available ambulances" value={dashboard.stats.availableAmbulances} note="Eligible for assignment" icon={AmbulanceIcon} tone="green" />
          <Metric label="Dispatched vehicles" value={dashboard.stats.dispatchedVehicles} note="Current assigned fleet" icon={Navigation} />
          <Metric label="Hospitals accepting" value={dashboard.stats.hospitalsAvailable} note="Based on local demo records" icon={Hospital} tone="green" />
          <Metric label="Avg response time" value={`${dashboard.stats.averageResponseTime} min`} note="Based on recorded demo dispatches" icon={Clock3} tone="amber" />
        </>}
      </div>
      <div className="mt-6 grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <Card><div className="mb-5 flex items-center justify-between"><div><h2 className="font-semibold text-white">Incident categories</h2><p className="mt-1 text-xs text-slate-500">Current database distribution</p></div><BarChart3 size={17} className="text-cyan-300" /></div><div className="h-64">{dashboard.distribution.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.distribution}><CartesianGrid stroke={chartGrid} strokeDasharray="3 3" /><XAxis dataKey="name" stroke="#94a3b8" /><YAxis stroke="#94a3b8" allowDecimals={false} /><Tooltip {...chartTooltip} /><Bar dataKey="value" radius={[6, 6, 0, 0]}>{dashboard.distribution.map((item, index) => <Cell key={item.name} fill={colors[index % colors.length]} />)}</Bar></BarChart></ResponsiveContainer> : <EmptyState title="No incident data" description="Create an emergency record to populate this chart." />}</div></Card>
        <Card><h2 className="font-semibold text-white">Priority mix</h2><p className="mt-1 text-xs text-slate-500">Categories are derived from persisted incidents</p><div className="h-64">{dashboard.distribution.length ? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={dashboard.distribution} dataKey="value" nameKey="name" innerRadius={54} outerRadius={82} paddingAngle={4}>{dashboard.distribution.map((item, index) => <Cell key={item.name} fill={colors[index % colors.length]} />)}</Pie><Tooltip {...chartTooltip} /></PieChart></ResponsiveContainer> : <EmptyState title="No priority data" description="Incident statistics will appear here." />}</div></Card>
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Card><div className="mb-4 flex items-center justify-between"><h2 className="font-semibold text-white">Recent emergencies</h2><Link to="/app/emergencies" className="text-xs text-cyan-300 hover:text-cyan-200">View all →</Link></div>{incidentsLoad.loading ? <Skeleton className="h-48" /> : active.length === 0 ? <EmptyState title="No active incidents" description="New emergencies appear here when recorded." /> : <div className="overflow-x-auto"><table className="w-full min-w-[560px] text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="pb-3">Incident</th><th className="pb-3">Priority</th><th className="pb-3">Status</th><th className="pb-3">Location</th></tr></thead><tbody>{active.slice(0, 5).map((incident) => <tr key={incident.id} className="border-t border-slate-800"><td className="py-3"><div className="font-medium text-slate-200">{incident.title}</div><div className="text-xs text-slate-500">{incident.category}</div></td><td className="py-3"><StatusChip tone={incident.severity === 'Critical' ? 'red' : incident.severity === 'High' ? 'amber' : 'cyan'}>{incident.severity}</StatusChip></td><td className="py-3 text-slate-300">{incident.status}</td><td className="py-3 text-xs text-slate-400">{incident.latitude.toFixed(3)}, {incident.longitude.toFixed(3)}</td></tr>)}</tbody></table></div>}</Card>
        <Card><div className="mb-4 flex items-center justify-between"><div><h2 className="font-semibold text-white">Activity timeline</h2><p className="mt-1 text-xs text-slate-500">Recent persisted system events</p></div><Activity size={17} className="text-cyan-300" /></div>{dashboard.activity.length === 0 ? <EmptyState title="No recent events" description="System activity will be recorded as the simulation runs." /> : <div className="space-y-4">{dashboard.activity.slice(0, 5).map((entry) => <div key={entry.id} className="flex gap-3"><span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-cyan-300" /><div className="min-w-0 flex-1"><div className="text-sm text-slate-300">{entry.message}</div><div className="mt-1 text-xs text-slate-600">{entry.time}</div></div></div>)}</div>}<div className="mt-5 border-t border-slate-800 pt-4 text-xs text-slate-600">Fleet records: {ambulancesLoad.data.length} · Hospital records: {hospitalsLoad.data.length}</div></Card>
      </div>
    </div>
  )
}

export function EmergenciesPage() {
  const [items, setItems] = useState<Emergency[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const { notify } = useToast()
  const refresh = useCallback(async () => { setLoading(true); setError(''); try { setItems(await api.emergencies.list()) } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load incidents') } finally { setLoading(false) } }, [])
  useEffect(() => { void refresh() }, [refresh])
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    try {
      await api.emergencies.create({ title: form.get('title'), category: form.get('category'), severity: form.get('severity'), latitude: Number(form.get('latitude')), longitude: Number(form.get('longitude')), description: form.get('description') })
      notify('Emergency recorded; dispatcher approval is required before assignment.', 'success')
      setShowForm(false)
      await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not record emergency') }
  }
  const updateStatus = async (incident: Emergency, status: string) => {
    try { await api.emergencies.update(incident.id, { status }); notify(`Incident ${incident.id} updated`, 'success'); await refresh() }
    catch (reason) { notify(reason instanceof Error ? reason.message : 'Update failed', 'error') }
  }
  return <div><PageTitle eyebrow="Incident response" title="Emergency management" description="Create, prioritize, and track incidents. Dispatch assignment is a separate approval step." action={<Button onClick={() => setShowForm((value) => !value)}><Plus size={16} /> New emergency</Button>} />{error && <ErrorMessage>{error}</ErrorMessage>}
    {showForm && <Card className="mb-5"><div className="mb-4 flex items-center justify-between"><h2 className="font-semibold text-white">Create emergency record</h2><button aria-label="Close form" onClick={() => setShowForm(false)}><XCircle size={18} className="text-slate-400" /></button></div><form onSubmit={submit} className="grid gap-4 md:grid-cols-2"><Field label="Incident title" name="title" required minLength={4} placeholder="Brief incident summary" /><SelectField label="Category" name="category"><option>Road Accident</option><option>Medical Emergency</option><option>Fire Emergency</option><option>Road Blockage</option></SelectField><SelectField label="Severity" name="severity"><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></SelectField><Field label="Latitude" name="latitude" type="number" step="any" min="-90" max="90" required /><Field label="Longitude" name="longitude" type="number" step="any" min="-180" max="180" required /><TextAreaField label="Description" name="description" rows={3} required minLength={8} placeholder="No real patient data. Describe the response need." /><div className="md:col-span-2"><Button type="submit">Save incident</Button></div></form></Card>}
    {loading ? <div className="space-y-3"><Skeleton className="h-24" /><Skeleton className="h-24" /><Skeleton className="h-24" /></div> : items.length === 0 ? <EmptyState title="No emergency records" description="Create a simulated record or submit a test request through the public SOS portal." /> : <Card className="!p-0"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-slate-950/50 text-xs uppercase text-slate-500"><tr>{['Incident', 'Category', 'Priority', 'Status', 'Assignment', 'Action'].map((name) => <th key={name} className="px-4 py-3">{name}</th>)}</tr></thead><tbody>{items.map((item) => <tr key={item.id} className="border-t border-slate-800"><td className="px-4 py-4"><div className="font-medium text-white">{item.title}</div><div className="mt-1 text-xs text-slate-500">{item.id} · {new Date(item.created_at).toLocaleString()}</div></td><td className="px-4 py-4 text-slate-300">{item.category}</td><td className="px-4 py-4"><StatusChip tone={item.severity === 'Critical' ? 'red' : item.severity === 'High' ? 'amber' : 'cyan'}>{item.severity}</StatusChip></td><td className="px-4 py-4 text-slate-300">{item.status}</td><td className="px-4 py-4 text-slate-400">{item.assigned_vehicle_id ?? 'Pending dispatcher'}</td><td className="px-4 py-4"><select aria-label={`Update status for ${item.id}`} value={item.status} onChange={(event) => void updateStatus(item, event.target.value)} className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-xs"><option>Open</option><option>Pending Approval</option><option>Dispatched</option><option>En Route</option><option>On Scene</option><option>Transporting</option><option>Resolved</option><option>Cancelled</option></select></td></tr>)}</tbody></table></div></Card>}</div>
}

export function MapPage() {
  const incidentLoad = usePageLoad(api.emergencies.list, [] as Emergency[])
  const fleetLoad = usePageLoad(api.ambulances.list, [] as Ambulance[])
  const hospitalLoad = usePageLoad(api.hospitals.list, [] as HospitalType[])
  const [route, setRoute] = useState<RouteResult | null>(null)
  const [error, setError] = useState('')
  const [algorithm, setAlgorithm] = useState('dijkstra')
  const [origin, setOrigin] = useState({ latitude: 40.706, longitude: -74.005 })
  const [destination, setDestination] = useState({ latitude: 40.748, longitude: -73.99 })
  const [simulateBlock, setSimulateBlock] = useState(false)
  const [roads, setRoads] = useState<Array<{ id: string; start: string; end: string; blocked: boolean; coordinates: [number, number][] }>>([])
  useEffect(() => {
    void api.request<typeof roads>('/routing/roads').then(setRoads).catch(() => setRoads([]))
  }, [])
  const calculate = async () => {
    setError('')
    try { setRoute(await api.routing.calculate({ origin, destination, algorithm, blocked_roads: simulateBlock ? [['Central Ave', 'City Center']] : [] })) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Route calculation failed') }
  }
  const coordinates = route?.coordinates
  const roadBlocks = route?.blocked_roads ?? []
  return <div><PageTitle eyebrow="Geospatial operations" title="Live operations map" description="Markers and routes use local synthetic records and the configured demo road graph. GPS is not live." action={<StatusChip tone="amber">GPS / traffic simulated</StatusChip>} />{error && <ErrorMessage>{error}</ErrorMessage>}
    <div className="grid gap-5 xl:grid-cols-[1fr_340px]"><Card className="!p-2"><div className="h-[540px] overflow-hidden rounded-xl"><MapContainer center={mapCenter} zoom={12} scrollWheelZoom className="h-full w-full"><TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />{roads.map((road) => road.coordinates.length === 2 && <Polyline key={road.id} positions={road.coordinates} pathOptions={{ color: road.blocked ? '#f87171' : '#64748b', weight: road.blocked ? 5 : 2, opacity: road.blocked ? 0.9 : 0.45, dashArray: road.blocked ? '5 8' : undefined }}><Popup>{road.start} → {road.end} · {road.blocked ? 'blocked' : 'simulated road'}</Popup></Polyline>)}{incidentLoad.data.map((item) => <CircleMarker key={item.id} center={[item.latitude, item.longitude]} radius={9} pathOptions={{ color: item.severity === 'Critical' ? '#ef4444' : '#22d3ee', fillColor: item.severity === 'Critical' ? '#ef4444' : '#22d3ee', fillOpacity: 0.9 }}><Popup>{item.title}<br />{item.severity} · {item.status}</Popup></CircleMarker>)}{fleetLoad.data.map((item) => <CircleMarker key={item.id} center={[item.latitude, item.longitude]} radius={6} pathOptions={{ color: '#fbbf24', fillColor: '#fbbf24', fillOpacity: 0.9 }}><Popup>{item.name} · {item.status}</Popup></CircleMarker>)}{hospitalLoad.data.map((item) => <CircleMarker key={item.id} center={[item.latitude, item.longitude]} radius={7} pathOptions={{ color: '#4ade80', fillColor: '#4ade80', fillOpacity: 0.8 }}><Popup>{item.name} · {item.available_beds} available beds</Popup></CircleMarker>)}{coordinates && <Polyline positions={coordinates} pathOptions={{ color: '#22d3ee', weight: 5 }} />}{roadBlocks.map((block, index) => block.coordinates?.length === 2 && <Polyline key={index} positions={block.coordinates} pathOptions={{ color: '#f87171', weight: 6, dashArray: '5 8' }}><Popup>Simulated blocked road: {block.start} → {block.end}</Popup></Polyline>)}</MapContainer></div></Card>
      <div className="space-y-5"><Card><h2 className="font-semibold text-white">Calculate route</h2><p className="mt-1 text-xs text-slate-500">Road-graph algorithm, not straight-line routing.</p><div className="mt-4 space-y-3"><Field label="Origin latitude" type="number" step="any" value={origin.latitude} onChange={(event) => setOrigin({ ...origin, latitude: Number(event.target.value) })} /><Field label="Origin longitude" type="number" step="any" value={origin.longitude} onChange={(event) => setOrigin({ ...origin, longitude: Number(event.target.value) })} /><Field label="Destination latitude" type="number" step="any" value={destination.latitude} onChange={(event) => setDestination({ ...destination, latitude: Number(event.target.value) })} /><Field label="Destination longitude" type="number" step="any" value={destination.longitude} onChange={(event) => setDestination({ ...destination, longitude: Number(event.target.value) })} /><SelectField label="Algorithm" value={algorithm} onChange={(event) => setAlgorithm(event.target.value)}><option value="dijkstra">Dijkstra</option><option value="astar">A*</option></SelectField><label className="flex items-center gap-2 text-xs text-amber-200"><input type="checkbox" checked={simulateBlock} onChange={(event) => setSimulateBlock(event.target.checked)} className="accent-amber-400" />Simulate Central Ave closure</label><Button className="w-full" onClick={() => void calculate()}><Route size={16} /> Calculate route</Button></div></Card>
        <Card><h2 className="font-semibold text-white">Route result</h2>{route ? <div className="mt-4 space-y-3 text-sm"><div className="flex justify-between"><span className="text-slate-400">Algorithm</span><span className="text-cyan-200">{route.algorithm}</span></div><div className="flex justify-between"><span className="text-slate-400">Graph distance</span><span>{route.distance.toFixed(2)} km</span></div><div className="flex justify-between"><span className="text-slate-400">Estimated travel</span><span>{route.estimated_travel_time_min ?? route.travel_cost} min</span></div><div className="flex justify-between"><span className="text-slate-400">Nodes explored</span><span>{route.nodes_explored}</span></div><div className="flex justify-between"><span className="text-slate-400">Execution</span><span>{route.execution_time_ms.toFixed(3)} ms</span></div><div className="border-t border-slate-800 pt-3 text-xs leading-6 text-slate-300">{route.path.join(' → ')}</div>{roadBlocks.map((block, index) => <div key={index} className="text-xs text-red-300">Simulated closure: {block.start} → {block.end}</div>)}</div> : <p className="mt-3 text-sm text-slate-500">Calculate a route to display graph output.</p>}</Card></div>
    </div></div>
}

export function AmbulancesPage() {
  const [items, setItems] = useState<Ambulance[]>([])
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const { notify } = useToast()
  const refresh = useCallback(async () => { try { setItems(await api.ambulances.list()); setError('') } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load ambulance fleet') } }, [])
  useEffect(() => { void refresh() }, [refresh])
  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const data = new FormData(event.currentTarget)
    try { await api.ambulances.create({ name: data.get('name'), vehicle_type: data.get('vehicle_type'), capacity: Number(data.get('capacity')), equipment: data.get('equipment'), latitude: Number(data.get('latitude')), longitude: Number(data.get('longitude')) }); notify('Vehicle added to fleet', 'success'); setFormOpen(false); await refresh() }
    catch (reason) { notify(reason instanceof Error ? reason.message : 'Could not add vehicle', 'error') }
  }
  const updateStatus = async (item: Ambulance, status: string) => {
    try { await api.ambulances.update(item.id, { ...item, status }); notify(`${item.name} status updated`, 'success'); await refresh() }
    catch (reason) { notify(reason instanceof Error ? reason.message : 'Could not update vehicle', 'error') }
  }
  return <div><PageTitle eyebrow="Fleet operations" title="Ambulance management" description="Manage vehicle readiness and equipment. Location values are seeded or operator-reported, not live telemetry." action={<Button onClick={() => setFormOpen((value) => !value)}><Plus size={16} /> Add vehicle</Button>} />{error && <ErrorMessage>{error}</ErrorMessage>}
    {formOpen && <Card className="mb-5"><form onSubmit={create} className="grid gap-4 md:grid-cols-2"><Field label="Unit name" name="name" required placeholder="A-104" /><SelectField label="Vehicle type" name="vehicle_type"><option>Ambulance</option><option>Fire Truck</option><option>Rescue Unit</option><option>Support Van</option></SelectField><Field label="Capacity" name="capacity" type="number" min="1" max="20" required defaultValue="2" /><Field label="Equipment" name="equipment" required defaultValue="Basic response kit" /><Field label="Latitude" name="latitude" type="number" step="any" min="-90" max="90" required defaultValue="40.73" /><Field label="Longitude" name="longitude" type="number" step="any" min="-180" max="180" required defaultValue="-74.00" /><Button type="submit">Save vehicle</Button><Button type="button" variant="secondary" onClick={() => setFormOpen(false)}>Cancel</Button></form></Card>}
    {items.length === 0 ? <EmptyState title="Fleet unavailable" description="Start the backend or add a vehicle to populate the fleet." /> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <Card key={item.id}><div className="flex items-start justify-between"><div className="flex items-center gap-3"><div className="rounded-xl bg-cyan-500/10 p-2.5 text-cyan-300"><AmbulanceIcon size={19} /></div><div><h2 className="font-semibold text-white">{item.name}</h2><p className="text-xs text-slate-500">{item.vehicle_type} · {item.capacity} seats</p></div></div><StatusChip tone={item.status === 'Available' ? 'green' : item.status === 'Out of Service' ? 'red' : 'amber'}>{item.status}</StatusChip></div><div className="mt-5 space-y-2 text-sm text-slate-400"><div className="flex justify-between"><span>Equipment</span><span className="text-right text-slate-300">{item.equipment}</span></div><div className="flex justify-between"><span>Last location</span><span className="text-slate-300">{item.latitude.toFixed(3)}, {item.longitude.toFixed(3)}</span></div><div className="flex justify-between"><span>Update freshness</span><span className="text-slate-300">{item.last_updated ? new Date(item.last_updated).toLocaleTimeString() : 'Seeded / unknown'}</span></div></div><SelectField className="mt-4" aria-label={`Status for ${item.name}`} label="Update status" value={item.status} onChange={(event) => void updateStatus(item, event.target.value)}><option>Available</option><option>Dispatched</option><option>En Route</option><option>On Scene</option><option>Transporting</option><option>Out of Service</option></SelectField></Card>)}</div>}</div>
}

export function HospitalsPage() {
  const [items, setItems] = useState<HospitalType[]>([])
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const { notify } = useToast()
  const refresh = useCallback(async () => { try { setItems(await api.hospitals.list()); setError('') } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load hospitals') } }, [])
  useEffect(() => { void refresh() }, [refresh])
  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const data = new FormData(event.currentTarget)
    try { await api.hospitals.create({ name: data.get('name'), latitude: Number(data.get('latitude')), longitude: Number(data.get('longitude')), available_beds: Number(data.get('beds')), icu_capacity: Number(data.get('icu')), emergency_facilities: data.get('facilities') }); notify('Hospital added', 'success'); setFormOpen(false); await refresh() }
    catch (reason) { notify(reason instanceof Error ? reason.message : 'Could not add hospital', 'error') }
  }
  return <div><PageTitle eyebrow="Care network" title="Hospital management" description="Track synthetic bed inventory, ICU resources, and acceptance status." action={<Button onClick={() => setFormOpen((value) => !value)}><Plus size={16} /> Register hospital</Button>} />{error && <ErrorMessage>{error}</ErrorMessage>}
    {formOpen && <Card className="mb-5"><form onSubmit={create} className="grid gap-4 md:grid-cols-2"><Field label="Hospital name" name="name" required /><Field label="Available beds" name="beds" type="number" min="0" required defaultValue="10" /><Field label="ICU capacity" name="icu" type="number" min="0" required defaultValue="2" /><Field label="Facilities" name="facilities" required defaultValue="Emergency department" /><Field label="Latitude" name="latitude" type="number" step="any" min="-90" max="90" required defaultValue="40.73" /><Field label="Longitude" name="longitude" type="number" step="any" min="-180" max="180" required defaultValue="-74.00" /><Button type="submit">Add hospital</Button><Button type="button" variant="secondary" onClick={() => setFormOpen(false)}>Cancel</Button></form></Card>}
    {items.length === 0 ? <EmptyState title="No hospital records" description="Register a hospital in the local demo network." /> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map((hospital) => <Card key={hospital.id}><div className="flex items-start justify-between"><div className="flex items-center gap-3"><div className="rounded-xl bg-emerald-500/10 p-2.5 text-emerald-300"><Hospital size={19} /></div><div><h2 className="font-semibold text-white">{hospital.name}</h2><p className="text-xs text-slate-500">{hospital.emergency_facilities}</p></div></div><StatusChip tone={hospital.accepting_patients === false ? 'red' : 'green'}>{hospital.accepting_patients === false ? 'Not accepting' : 'Accepting'}</StatusChip></div><div className="mt-5 grid grid-cols-2 gap-3"><div className="rounded-xl bg-slate-950/60 p-3"><BedDouble size={16} className="text-cyan-300" /><div className="mt-2 text-xl font-semibold text-white">{hospital.available_beds}</div><div className="text-xs text-slate-500">Available beds</div></div><div className="rounded-xl bg-slate-950/60 p-3"><Stethoscope size={16} className="text-emerald-300" /><div className="mt-2 text-xl font-semibold text-white">{hospital.icu_capacity}</div><div className="text-xs text-slate-500">ICU capacity</div></div></div><div className="mt-3 text-xs text-slate-600">Location: {hospital.latitude.toFixed(3)}, {hospital.longitude.toFixed(3)}</div></Card>)}</div>}</div>
}

export function DispatchPage() {
  const emergencyLoad = usePageLoad(api.emergencies.list, [] as Emergency[])
  const ambulanceLoad = usePageLoad(api.ambulances.list, [] as Ambulance[])
  const [dispatches, setDispatches] = useState<Array<Record<string, unknown>>>([])
  const [selected, setSelected] = useState('')
  const [recommendation, setRecommendation] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')
  const { notify } = useToast()
  const refresh = useCallback(async () => { try { setDispatches(await api.dispatch.list()) } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load dispatch records') } }, [])
  useEffect(() => { void refresh() }, [refresh])
  const propose = async (id: string) => { setSelected(id); setError(''); try { setRecommendation(await api.dispatch.recommend(id)) } catch (reason) { setRecommendation(null); setError(reason instanceof Error ? reason.message : 'No recommendation available') } }
  const approve = async (vehicleId: string) => {
    if (!selected) return
    try { await api.dispatch.approve(selected, vehicleId); notify('Dispatch approved; vehicle assignment recorded.', 'success'); setRecommendation(null); setSelected(''); await Promise.all([refresh(), emergencyLoad.refresh(), ambulanceLoad.refresh()]) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Dispatch approval failed') }
  }
  const openItems = emergencyLoad.data.filter((item) => !item.assigned_vehicle_id && !['Resolved', 'Cancelled'].includes(item.status))
  return <div><PageTitle eyebrow="Resource allocation" title="Dispatch center" description="Review algorithmic recommendations and explicitly approve assignment. No automatic dispatch." />{error && <ErrorMessage>{error}</ErrorMessage>}
    <div className="grid gap-5 xl:grid-cols-[1fr_0.9fr]"><Card><h2 className="mb-4 font-semibold text-white">Awaiting assignment</h2>{emergencyLoad.loading ? <Skeleton className="h-36" /> : openItems.length === 0 ? <EmptyState title="Queue is clear" description="Unassigned active incidents will appear here." /> : <div className="space-y-3">{openItems.map((item) => <div key={item.id} className="flex flex-col justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:flex-row sm:items-center"><div><div className="font-medium text-white">{item.title}</div><div className="mt-1 text-xs text-slate-500">{item.category} · {item.severity} · {item.id}</div></div><Button onClick={() => void propose(item.id)}>Find resource</Button></div>)}</div>}</Card>
      <Card><h2 className="font-semibold text-white">Recommendation review</h2>{recommendation ? <div className="mt-4"><div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-4"><div className="text-sm text-cyan-100">{String(recommendation.reason ?? 'Recommended by resource suitability and road-graph distance.')}</div>{typeof recommendation.vehicle === 'object' && recommendation.vehicle !== null && <div className="mt-3 text-sm text-slate-300">Vehicle: {String((recommendation.vehicle as Record<string, unknown>).name ?? '')} · ETA estimate {String(recommendation.estimated_travel_time_min ?? '—')} min</div>}</div>{ambulanceLoad.data.filter((vehicle) => vehicle.status === 'Available').map((vehicle) => <div key={vehicle.id} className="mt-3 flex items-center justify-between rounded-xl border border-slate-800 p-3"><div><div className="text-sm text-white">{vehicle.name}</div><div className="text-xs text-slate-500">{vehicle.vehicle_type} · {vehicle.equipment}</div></div><Button onClick={() => void approve(vehicle.id)}>Approve</Button></div>)}</div> : <p className="mt-3 text-sm text-slate-500">Select an unassigned incident to calculate and review a dispatch recommendation.</p>}</Card></div>
    <Card className="mt-5"><h2 className="font-semibold text-white">Dispatch history</h2>{dispatches.length === 0 ? <p className="mt-3 text-sm text-slate-500">No approved dispatches have been recorded.</p> : <div className="mt-3 space-y-2">{dispatches.map((item, index) => <div key={String(item.id ?? index)} className="flex flex-wrap justify-between gap-2 border-t border-slate-800 py-3 text-sm"><span className="text-slate-300">Incident {String(item.emergency_id ?? '')} → {String(item.vehicle_id ?? '')}</span><span className="text-slate-500">{String(item.status ?? '')}</span></div>)}</div>}</Card></div>
}

export function AnalyticsPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { void api.request<Record<string, unknown>>('/analytics').then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unable to load analytics')) }, [])
  const daily = (data?.daily ?? []) as Array<Record<string, number | string>>
  const monthly = (data?.monthly ?? []) as Array<Record<string, number | string>>
  const weekly = (data?.weekly ?? []) as Array<Record<string, number | string>>
  return <div><PageTitle eyebrow="Operational intelligence" title="Analytics" description="Trends are calculated from stored simulation records. No performance figures are fabricated." action={<StatusChip tone="amber">Synthetic seed dataset</StatusChip>} />{error && <ErrorMessage>{error}</ErrorMessage>}
    {!data && !error ? <Skeleton className="h-80" /> : <div className="space-y-5"><div className="grid gap-5 xl:grid-cols-2"><Card><h2 className="mb-4 font-semibold text-white">Daily emergency trend</h2><div className="h-72">{daily.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={daily}><CartesianGrid stroke={chartGrid} strokeDasharray="3 3" /><XAxis dataKey="label" stroke="#94a3b8" /><YAxis stroke="#94a3b8" allowDecimals={false} /><Tooltip {...chartTooltip} /><Bar dataKey="incidents" fill="#22d3ee" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer> : <EmptyState title="Insufficient data" description="Daily trends appear as records accumulate." />}</div></Card><Card><h2 className="mb-4 font-semibold text-white">Weekly response time</h2><div className="h-72">{weekly.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={weekly}><CartesianGrid stroke={chartGrid} strokeDasharray="3 3" /><XAxis dataKey="label" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><Tooltip {...chartTooltip} /><Line type="monotone" dataKey="responseTime" stroke="#4ade80" strokeWidth={3} /></LineChart></ResponsiveContainer> : <EmptyState title="No response metrics" description="Response metrics need completed dispatches." />}</div></Card></div><Card><h2 className="mb-4 font-semibold text-white">Monthly incidents</h2><div className="h-72">{monthly.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={monthly}><CartesianGrid stroke={chartGrid} strokeDasharray="3 3" /><XAxis dataKey="label" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><Tooltip {...chartTooltip} /><Area type="monotone" dataKey="incidents" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.18} /></AreaChart></ResponsiveContainer> : <EmptyState title="No monthly records" description="Monthly aggregates will be available when enough incidents exist." />}</div></Card></div>}</div>
}

export function DsaLabPage() {
  const [algorithm, setAlgorithm] = useState('dijkstra')
  const [source, setSource] = useState('North Hub')
  const [destination, setDestination] = useState('South Ward')
  const [trace, setTrace] = useState<AlgorithmTrace | null>(null)
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [error, setError] = useState('')
  const { notify } = useToast()
  const nodes = ['North Hub', 'Central Ave', 'Medical District', 'City Center', 'Old Town', 'East Connector', 'River East', 'South Ward', 'Harbor Point']
  useEffect(() => {
    if (!playing || !trace) return
    const timer = window.setInterval(() => setStep((current) => {
      if (current >= trace.trace.length) { setPlaying(false); return current }
      return current + 1
    }), 700)
    return () => window.clearInterval(timer)
  }, [playing, trace])
  const run = async () => {
    setError(''); setPlaying(false); setStep(0)
    try { setTrace(await api.dsa.run({ algorithm, source, destination })); notify('Algorithm trace returned by the backend.', 'success') }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Algorithm execution failed') }
  }
  const visible = trace?.trace.slice(0, step) ?? []
  const visited = new Set(visible.filter((item) => item.state === 'visited').map((item) => item.node))
  const current = visible.findLast?.((item) => item.state === 'current')?.node
  return <div><PageTitle eyebrow="Algorithm workspace" title="DSA laboratory" description="Trace visualization is generated by the backend algorithm implementation; timings are measured per run." action={<StatusChip tone="cyan">Actual execution trace</StatusChip>} />{error && <ErrorMessage>{error}</ErrorMessage>}
    <div className="grid gap-5 xl:grid-cols-[340px_1fr]"><Card><h2 className="font-semibold text-white">Run configuration</h2><div className="mt-4 space-y-3"><SelectField label="Algorithm" value={algorithm} onChange={(event) => setAlgorithm(event.target.value)}><option value="dijkstra">Dijkstra</option><option value="astar">A*</option><option value="bfs">Breadth-first search</option><option value="dfs">Depth-first search</option></SelectField><SelectField label="Source" value={source} onChange={(event) => setSource(event.target.value)}>{nodes.map((node) => <option key={node}>{node}</option>)}</SelectField><SelectField label="Destination" value={destination} onChange={(event) => setDestination(event.target.value)}>{nodes.map((node) => <option key={node}>{node}</option>)}</SelectField><Button className="w-full" onClick={() => void run()}><BrainCircuit size={16} /> Run algorithm</Button></div><div className="mt-5 border-t border-slate-800 pt-4"><div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Trace controls</div><div className="mt-3 grid grid-cols-2 gap-2"><Button variant="secondary" disabled={!trace || step === 0} onClick={() => { setPlaying(false); setStep(0) }}>Reset</Button><Button variant="secondary" disabled={!trace || step >= (trace?.trace.length ?? 0)} onClick={() => setStep((value) => Math.min(value + 1, trace?.trace.length ?? 0))}>Step</Button><Button variant="secondary" disabled={!trace || step >= (trace?.trace.length ?? 0)} onClick={() => setPlaying((value) => !value)}>{playing ? 'Pause' : 'Play'}</Button><Button variant="secondary" disabled={!trace} onClick={() => { setPlaying(false); setStep(trace?.trace.length ?? 0) }}>Finish</Button></div></div></Card>
      <div className="space-y-5"><Card><div className="mb-4 flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-semibold text-white">Graph traversal</h2><p className="mt-1 text-xs text-slate-500">Current / visited / final path states</p></div><div className="flex gap-2"><StatusChip tone="cyan">Current</StatusChip><StatusChip tone="green">Visited</StatusChip><StatusChip tone="amber">Path</StatusChip></div></div><div className="grid min-h-[300px] grid-cols-2 gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:grid-cols-3 lg:grid-cols-5">{nodes.map((node) => { const finalPath = trace?.path.includes(node); const isCurrent = current === node; const isVisited = visited.has(node); return <div key={node} className={`flex min-h-20 items-center justify-center rounded-xl border text-center text-sm transition ${isCurrent ? 'border-cyan-300 bg-cyan-400/15 text-cyan-100 shadow-glow' : finalPath ? 'border-amber-300/50 bg-amber-400/10 text-amber-100' : isVisited ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : 'border-slate-800 bg-slate-900 text-slate-400'}`}>{node}</div> })}</div><div className="mt-3 flex items-center justify-between text-xs text-slate-500"><span>Step {step} / {trace?.trace.length ?? 0}</span><span>Trace states: {visible.length}</span></div></Card>
        <Card><h2 className="font-semibold text-white">Execution results</h2>{trace ? <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><div><div className="text-xs text-slate-500">Path distance</div><div className="mt-1 text-xl text-white">{trace.distance.toFixed(2)} km</div></div><div><div className="text-xs text-slate-500">Nodes explored</div><div className="mt-1 text-xl text-white">{trace.nodes_explored}</div></div><div><div className="text-xs text-slate-500">Measured time</div><div className="mt-1 text-xl text-white">{trace.execution_time_ms.toFixed(3)} ms</div></div><div><div className="text-xs text-slate-500">Complexity</div><div className="mt-1 text-sm text-white">{trace.time_complexity} / {trace.space_complexity}</div></div><div className="sm:col-span-2 lg:col-span-4 border-t border-slate-800 pt-3 text-sm text-cyan-200">{trace.path.join(' → ')}</div></div> : <p className="mt-3 text-sm text-slate-500">Run an algorithm to view the trace and measured result.</p>}</Card></div></div>
  </div>
}

export function PublicSosPage() {
  const [category, setCategory] = useState('Medical Emergency')
  const [description, setDescription] = useState('')
  const [contact, setContact] = useState('')
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null)
  const [gpsState, setGpsState] = useState<'idle' | 'loading' | 'denied' | 'ready'>('idle')
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { notify } = useToast()
  const navigate = useNavigate()
  const captureLocation = () => {
    if (!navigator.geolocation) { setGpsState('denied'); return }
    setGpsState('loading')
    navigator.geolocation.getCurrentPosition(
      (position) => { setLocation({ latitude: position.coords.latitude, longitude: position.coords.longitude }); setGpsState('ready') },
      () => { setGpsState('denied'); setError('Location access was not granted. You may enter coordinates manually.') },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
    )
  }
  const submit = async () => {
    if (!location) { setError('Provide a GPS location or enter coordinates before submitting.'); return }
    setBusy(true); setError('')
    try {
      const item = await api.publicSos.create({ category, severity: 'High', description, contact, latitude: location.latitude, longitude: location.longitude, confirmation: true })
      localStorage.setItem(`resqnet.sos.cancel.${item.id}`, item.cancel_token)
      notify('SOS request recorded in the local simulation.', 'success')
      navigate(`/sos/track/${item.id}`)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'SOS request failed') }
    finally { setBusy(false); setConfirm(false) }
  }
  return <div className="min-h-screen bg-[#080d18] px-4 py-6 text-slate-100"><div className="mx-auto max-w-xl"><div className="mb-6 flex items-center justify-between"><Link to="/" className="font-bold tracking-[0.16em] text-cyan-200">RESQNET</Link><StatusChip tone="amber">Demo only</StatusChip></div><Card><div className="text-center"><div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-red-500/10 text-red-300"><Siren size={27} /></div><h1 className="mt-4 text-2xl font-semibold text-white">Public SOS portal</h1><p className="mx-auto mt-2 max-w-md text-sm text-slate-400">This demonstration does not contact emergency services. For a real emergency, call your local emergency number now.</p></div>
      {error && <div className="mt-4"><ErrorMessage>{error}</ErrorMessage></div>}
      <div className="mt-6 space-y-4"><SelectField label="Emergency category" value={category} onChange={(event) => setCategory(event.target.value)}><option>Medical Emergency</option><option>Road Accident</option><option>Fire Emergency</option><option>Road Blockage</option></SelectField><TextAreaField label="What happened? (no private medical details)" value={description} onChange={(event) => setDescription(event.target.value)} rows={3} maxLength={500} placeholder="Short description of response need" /><Field label="Callback contact (optional)" type="tel" value={contact} onChange={(event) => setContact(event.target.value)} maxLength={40} placeholder="Phone number" /><div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex items-center justify-between gap-3"><div><div className="text-sm font-medium text-white">Location</div><div className="mt-1 text-xs text-slate-500">{location ? `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}` : gpsState === 'denied' ? 'Location unavailable' : 'Location not captured'}</div></div><Button variant="secondary" onClick={captureLocation} disabled={gpsState === 'loading'}><Crosshair size={15} />{gpsState === 'loading' ? 'Locating…' : 'Use my location'}</Button></div><div className="mt-3 grid grid-cols-2 gap-3"><Field label="Latitude" type="number" step="any" min="-90" max="90" value={location?.latitude ?? ''} onChange={(event) => { const latitude = Number(event.target.value); setLocation((current) => ({ latitude, longitude: current?.longitude ?? 0 })) }} /><Field label="Longitude" type="number" step="any" min="-180" max="180" value={location?.longitude ?? ''} onChange={(event) => { const longitude = Number(event.target.value); setLocation((current) => ({ latitude: current?.latitude ?? 0, longitude })) }} /></div><p className="mt-2 text-xs text-slate-600">GPS coordinates are shared only after you submit. Device permission is requested by your browser.</p></div><Button variant="danger" className="w-full !py-4 text-base" disabled={busy} onClick={() => { if (!description.trim()) { setError('Add a short description before continuing.'); return } if (!location) { setError('Capture or enter a location before continuing.'); return } setConfirm(true) }}><Siren size={18} />Review SOS request</Button></div>
      <div className="mt-5 border-t border-slate-800 pt-4 text-xs leading-5 text-slate-500">Two-step confirmation helps prevent accidental activation. You can cancel before submission. This local app does not send SMS, call dispatch, or guarantee assistance.</div>
    </Card></div>{confirm && <ConfirmDialog title="Submit simulated SOS?" description={`This sends a synthetic ${category.toLowerCase()} request to the RESQNET local demo backend at ${location?.latitude.toFixed(4)}, ${location?.longitude.toFixed(4)}. It will not contact emergency services.`} confirmText={busy ? 'Submitting…' : 'Submit SOS'} onCancel={() => setConfirm(false)} onConfirm={() => { if (!busy) void submit() }} />}</div>
}

export function SosTrackingPage() {
  const { id = '' } = useParams()
  const [item, setItem] = useState<Emergency | null>(null)
  const [error, setError] = useState('')
  const [confirmCancel, setConfirmCancel] = useState(false)
  const { notify } = useToast()
  const refresh = useCallback(async () => { try { setItem(await api.publicSos.track(id)); setError('') } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load request') } }, [id])
  useEffect(() => { void refresh() }, [refresh])
  const cancel = async () => {
    try { await api.publicSos.cancel(id); notify('Request cancellation recorded.', 'success'); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Cancellation failed') }
    finally { setConfirmCancel(false) }
  }
  return <div className="min-h-screen bg-[#080d18] px-4 py-8 text-slate-100"><div className="mx-auto max-w-xl"><Link to="/" className="text-sm text-cyan-200">← RESQNET</Link><Card className="mt-5"><div className="flex items-center gap-3"><div className="rounded-xl bg-cyan-500/10 p-3 text-cyan-200"><Activity size={20} /></div><div><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Demo request tracking</div><h1 className="text-xl font-semibold text-white">Request {id}</h1></div></div>{error && <div className="mt-4"><ErrorMessage>{error}</ErrorMessage></div>}{item && <><div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex items-center justify-between"><span className="text-sm text-slate-400">Current status</span><StatusChip tone={item.status === 'Resolved' ? 'green' : item.status === 'Cancelled' ? 'slate' : 'amber'}>{item.status}</StatusChip></div><div className="mt-4 text-lg font-medium text-white">{item.title}</div><div className="mt-1 text-sm text-slate-400">{item.category} · {item.severity}</div><div className="mt-4 text-xs text-slate-500">Location: {item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}</div></div><div className="mt-5 flex flex-wrap gap-3"><Button variant="secondary" onClick={() => void refresh()}>Refresh status</Button>{!['Cancelled', 'Resolved'].includes(item.status) && <Button variant="danger" onClick={() => setConfirmCancel(true)}>Request cancellation</Button>}</div></>}<p className="mt-6 text-xs leading-5 text-amber-200/70">This page tracks records in a simulation only. It does not confirm that responders have been notified or dispatched.</p></Card></div>{confirmCancel && <ConfirmDialog title="Request cancellation?" description="Cancellation requires the one-time token stored in this browser when the SOS was submitted." confirmText="Submit cancellation" onCancel={() => setConfirmCancel(false)} onConfirm={() => void cancel()} />}</div>
}

export function AmbulanceOperatorPage() {
  const { user } = useAuth()
  const [items, setItems] = useState<Ambulance[]>([])
  const [selected, setSelected] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { notify } = useToast()
  const refresh = useCallback(async () => { try { const fleet = await api.ambulances.list(); setItems(fleet); setError('') } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load operator data') } }, [])
  useEffect(() => { void refresh() }, [refresh])
  const updateLocation = () => {
    if (!selected) { setError('Select a vehicle assigned to your operator account.'); return }
    if (!navigator.geolocation) { setError('Geolocation is not available in this browser.'); return }
    setBusy(true); navigator.geolocation.getCurrentPosition(async (position) => {
      try { await api.ambulances.location(selected, position.coords.latitude, position.coords.longitude); notify('Operator-reported location updated.', 'success'); await refresh() }
      catch (reason) { setError(reason instanceof Error ? reason.message : 'Location update failed') }
      finally { setBusy(false) }
    }, () => { setError('Location permission was denied or timed out.'); setBusy(false) }, { enableHighAccuracy: false, timeout: 10000 })
  }
  const vehicle = items.find((item) => item.id === selected)
  return <div><PageTitle eyebrow="Field operator" title="Ambulance operator portal" description={`Signed in as ${user?.username ?? 'operator'}. Location sharing is operator-initiated and should be treated as simulated/demo data.`} /><StatusChip tone="amber">No live vehicle tracking</StatusChip>{error && <div className="mt-4"><ErrorMessage>{error}</ErrorMessage></div>}<div className="mt-5 grid gap-5 lg:grid-cols-2"><Card><h2 className="font-semibold text-white">My vehicle</h2><div className="mt-4"><SelectField label="Assigned vehicle" value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Select a vehicle</option>{items.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.status}</option>)}</SelectField></div>{vehicle && <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4"><div className="font-medium text-white">{vehicle.name}</div><div className="mt-1 text-sm text-slate-400">{vehicle.vehicle_type} · {vehicle.equipment}</div><div className="mt-3 text-xs text-slate-500">Last recorded: {vehicle.latitude.toFixed(5)}, {vehicle.longitude.toFixed(5)} · {vehicle.last_updated ? new Date(vehicle.last_updated).toLocaleString() : 'unknown update time'}</div></div>}<Button className="mt-4" disabled={busy} onClick={updateLocation}><Navigation size={16} />Share current location</Button></Card><Card><h2 className="font-semibold text-white">Operator safety</h2><ul className="mt-4 space-y-3 text-sm text-slate-400"><li>• Use this portal only in a controlled training environment.</li><li>• Location is requested only after pressing “Share current location.”</li><li>• No background tracking is performed by this frontend.</li><li>• Incident status updates should be coordinated with dispatch.</li></ul></Card></div></div>
}

export function HospitalOperatorPage() {
  const [items, setItems] = useState<HospitalType[]>([])
  const [selected, setSelected] = useState('')
  const [beds, setBeds] = useState('')
  const [error, setError] = useState('')
  const refresh = useCallback(async () => { try { setItems(await api.hospitals.list()); setError('') } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load hospital data') } }, [])
  useEffect(() => { void refresh() }, [refresh])
  const hospital = items.find((item) => item.id === selected)
  const update = async (event: FormEvent) => {
    event.preventDefault()
    if (!hospital) return
    try { await api.request(`/hospitals/${hospital.id}/resources`, { method: 'PATCH', body: JSON.stringify({ available_beds: Number(beds), accepting_patients: hospital.accepting_patients !== false }) }); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Resource update failed') }
  }
  const toggleAccepting = async () => {
    if (!hospital) return
    try { await api.request(`/hospitals/${hospital.id}/resources`, { method: 'PATCH', body: JSON.stringify({ available_beds: hospital.available_beds, accepting_patients: hospital.accepting_patients === false }) }); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Status update failed') }
  }
  return <div><PageTitle eyebrow="Care provider" title="Hospital operator portal" description="Update synthetic bed availability and acceptance status for this demonstration network." />{error && <ErrorMessage>{error}</ErrorMessage>}<Card className="max-w-2xl"><SelectField label="Hospital" value={selected} onChange={(event) => { setSelected(event.target.value); const value = items.find((item) => item.id === event.target.value); setBeds(String(value?.available_beds ?? '')) }}><option value="">Select a hospital</option>{items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField>{hospital && <><div className="my-4 rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex items-center justify-between"><div className="font-medium text-white">{hospital.name}</div><StatusChip tone={hospital.accepting_patients === false ? 'red' : 'green'}>{hospital.accepting_patients === false ? 'Not accepting' : 'Accepting'}</StatusChip></div><div className="mt-2 text-sm text-slate-400">ICU capacity: {hospital.icu_capacity} · Facilities: {hospital.emergency_facilities}</div></div><form onSubmit={update} className="space-y-4"><Field label="Available beds" type="number" min="0" max="10000" required value={beds} onChange={(event) => setBeds(event.target.value)} /><div className="flex flex-wrap gap-3"><Button type="submit">Save bed count</Button><Button type="button" variant="secondary" onClick={() => void toggleAccepting()}>{hospital.accepting_patients === false ? 'Accept patients' : 'Pause acceptance'}</Button></div></form></>}</Card></div>
}

export function ProfilePage() {
  const { user } = useAuth()
  return <div><PageTitle eyebrow="Account" title="User profile" description="Identity and role information for the currently authenticated local account." /><Card className="max-w-2xl"><div className="flex items-center gap-4"><div className="grid h-14 w-14 place-items-center rounded-2xl bg-cyan-500/10 text-xl font-semibold text-cyan-200">{user?.username.slice(0, 2).toUpperCase()}</div><div><h2 className="text-lg font-semibold text-white">{user?.username}</h2><div className="text-sm text-slate-400">{user?.role}</div></div></div><div className="mt-6 grid gap-4 border-t border-slate-800 pt-5 sm:grid-cols-2"><div><div className="text-xs text-slate-500">Email</div><div className="mt-1 text-sm text-slate-200">{user?.email}</div></div><div><div className="text-xs text-slate-500">Account ID</div><div className="mt-1 text-sm text-slate-200">{user?.id}</div></div></div><p className="mt-5 text-xs text-slate-600">Sensitive profile and permission changes are managed by an administrator. This demo currently exposes read-only profile details.</p></Card></div>
}

export function SettingsPage() {
  const [theme, setTheme] = useState(localStorage.getItem('resqnet.theme') ?? 'dark')
  const [compact, setCompact] = useState(localStorage.getItem('resqnet.compact') === 'true')
  const { notify } = useToast()
  const save = () => {
    localStorage.setItem('resqnet.theme', theme)
    localStorage.setItem('resqnet.compact', String(compact))
    document.documentElement.dataset.theme = theme
    document.documentElement.dataset.compact = String(compact)
    notify('Preferences saved on this device.', 'success')
  }
  return <div><PageTitle eyebrow="Preferences" title="Settings" description="UI preferences are stored locally in this browser." /><Card className="max-w-2xl"><h2 className="font-semibold text-white">Appearance</h2><div className="mt-4 space-y-4"><SelectField label="Color theme" value={theme} onChange={(event) => setTheme(event.target.value)}><option value="dark">Dark</option><option value="light">Light (experimental)</option></SelectField><label className="flex items-center gap-3 text-sm text-slate-300"><input type="checkbox" checked={compact} onChange={(event) => setCompact(event.target.checked)} className="accent-cyan-400" />Enable compact data tables</label><Button onClick={save}>Save preferences</Button></div><div className="mt-6 border-t border-slate-800 pt-5"><h3 className="font-medium text-white">Data and privacy</h3><p className="mt-2 text-sm text-slate-400">Seed records are fictional demo information. Do not enter actual patient data. The local browser stores access tokens for this demo session.</p></div></Card></div>
}

export function NotFoundPage() {
  return <div className="grid min-h-[70vh] place-items-center text-center"><div><div className="text-6xl font-bold text-cyan-300">404</div><h1 className="mt-3 text-2xl font-semibold text-white">Page not found</h1><p className="mt-2 text-slate-400">This route is not part of the RESQNET demo.</p><Link to="/" className="mt-5 inline-block rounded-xl bg-cyan-400 px-4 py-2.5 font-medium text-slate-950">Return home</Link></div></div>
}
