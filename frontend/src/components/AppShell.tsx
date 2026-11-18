import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity, Ambulance, Bell, BrainCircuit, Building2, ChevronDown, ChevronLeft, ChevronRight,
  Command, Gauge, LogOut, MapPinned, Menu, Search, Settings, ShieldAlert, Siren, UserRound, X,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from './Ui'
import { StatusChip } from './Ui'

const links = [
  { to: '/app/dashboard', label: 'Command Center', icon: Gauge },
  { to: '/app/emergencies', label: 'Emergency Management', icon: Siren },
  { to: '/app/map', label: 'Live Operations Map', icon: MapPinned },
  { to: '/app/ambulances', label: 'Ambulance Management', icon: Ambulance },
  { to: '/app/hospitals', label: 'Hospital Management', icon: Building2 },
  { to: '/app/dispatch', label: 'Dispatch Center', icon: Activity },
  { to: '/app/analytics', label: 'Analytics', icon: Activity },
  { to: '/app/dsa', label: 'DSA Laboratory', icon: BrainCircuit },
]

export function AppShell() {
  const [collapsed, setCollapsed] = useState(localStorage.getItem('resqnet.sidebar') === 'collapsed')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [live, setLive] = useState<'connecting' | 'connected' | 'offline'>('connecting')
  const [events, setEvents] = useState<string[]>([])
  const retryRef = useRef(0)
  const { user, logout } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    let active = true
    let socket: WebSocket | undefined
    let timer: number | undefined
    const connect = () => {
      if (!active) return
      const token = localStorage.getItem('resqnet.access')
      if (!token) {
        setLive('offline')
        return
      }
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const socketUrl = `${protocol}//${window.location.host}/api/v1/ws/updates?token=${encodeURIComponent(token)}`
      socket = new WebSocket(socketUrl)
      socket.onopen = () => { retryRef.current = 0; setLive('connected') }
      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as { message?: string }
          if (parsed.message) {
            setEvents((current) => [parsed.message as string, ...current].slice(0, 5))
            notify(parsed.message, 'info')
          }
        } catch {
          setEvents((current) => ['Received a live update', ...current].slice(0, 5))
        }
      }
      socket.onerror = () => setLive('offline')
      socket.onclose = () => {
        setLive('offline')
        if (active && retryRef.current < 5) {
          const wait = Math.min(1000 * (2 ** retryRef.current), 16000)
          retryRef.current += 1
          timer = window.setTimeout(connect, wait)
        }
      }
    }
    connect()
    return () => {
      active = false
      if (timer) window.clearTimeout(timer)
      socket?.close()
    }
  }, [notify, location.pathname])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return query ? links.filter((item) => item.label.toLowerCase().includes(query)) : []
  }, [search])

  const toggleSidebar = () => {
    setCollapsed((value) => {
      localStorage.setItem('resqnet.sidebar', value ? 'expanded' : 'collapsed')
      return !value
    })
  }

  const sidebar = (
    <aside className={`flex h-full flex-col border-slate-800 bg-[#0b1220] transition-all ${collapsed ? 'w-[76px]' : 'w-[270px]'}`}>
      <div className={`flex h-[76px] items-center border-b border-slate-800 ${collapsed ? 'justify-center px-2' : 'justify-between px-5'}`}>
        <Link to="/app/dashboard" aria-label="RESQNET command center" className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400 text-slate-950"><ShieldAlert size={20} /></div>
          {!collapsed && <div><div className="font-bold tracking-[0.15em] text-white">RESQNET</div><div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Response network</div></div>}
        </Link>
        {!collapsed && <button className="hidden rounded-lg p-2 text-slate-500 hover:bg-slate-800 hover:text-white lg:block" onClick={toggleSidebar} aria-label="Collapse sidebar"><ChevronLeft size={17} /></button>}
      </div>
      <div className="border-b border-slate-800 px-3 py-3">
        {!collapsed && <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">Operations</div>}
        <nav className="space-y-1" aria-label="Primary navigation">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} title={collapsed ? label : undefined} onClick={() => setMobileOpen(false)}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${isActive ? 'bg-cyan-400/10 font-medium text-cyan-200 ring-1 ring-cyan-400/15' : 'text-slate-400 hover:bg-slate-800/80 hover:text-white'} ${collapsed ? 'justify-center' : ''}`}>
              <Icon size={18} /><span className={collapsed ? 'sr-only' : ''}>{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
      <div className="border-b border-slate-800 px-3 py-3">
        {!collapsed && <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">Portals</div>}
        <nav className="space-y-1" aria-label="Operator portals">
          <NavLink to="/operator/ambulance" title={collapsed ? 'Ambulance operator portal' : undefined} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? 'bg-cyan-400/10 text-cyan-200' : 'text-slate-400 hover:bg-slate-800 hover:text-white'} ${collapsed ? 'justify-center' : ''}`}><Ambulance size={18} /><span className={collapsed ? 'sr-only' : ''}>Ambulance Operator</span></NavLink>
          <NavLink to="/operator/hospital" title={collapsed ? 'Hospital operator portal' : undefined} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? 'bg-cyan-400/10 text-cyan-200' : 'text-slate-400 hover:bg-slate-800 hover:text-white'} ${collapsed ? 'justify-center' : ''}`}><Building2 size={18} /><span className={collapsed ? 'sr-only' : ''}>Hospital Operator</span></NavLink>
        </nav>
      </div>
      <div className="mt-auto space-y-1 border-t border-slate-800 p-3">
        <NavLink to="/app/profile" title={collapsed ? 'User profile' : undefined} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? 'bg-cyan-400/10 text-cyan-200' : 'text-slate-400 hover:bg-slate-800 hover:text-white'} ${collapsed ? 'justify-center' : ''}`}><UserRound size={18} /><span className={collapsed ? 'sr-only' : ''}>Profile</span></NavLink>
        <NavLink to="/app/settings" title={collapsed ? 'Settings' : undefined} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? 'bg-cyan-400/10 text-cyan-200' : 'text-slate-400 hover:bg-slate-800 hover:text-white'} ${collapsed ? 'justify-center' : ''}`}><Settings size={18} /><span className={collapsed ? 'sr-only' : ''}>Settings</span></NavLink>
        {collapsed && <button className="flex w-full justify-center rounded-xl px-3 py-2.5 text-slate-400 hover:bg-slate-800" onClick={toggleSidebar} aria-label="Expand sidebar"><ChevronRight size={18} /></button>}
        {!collapsed && <div className="px-3 pt-2 text-[10px] text-slate-600">BUILD · LOCAL SIMULATION</div>}
      </div>
    </aside>
  )

  return (
    <div className="min-h-screen bg-[#080d18] text-slate-100 lg:flex">
      <div className="hidden lg:block">{sidebar}</div>
      {mobileOpen && <div className="fixed inset-0 z-[1000] bg-black/60 lg:hidden" onClick={() => setMobileOpen(false)}><div className="h-full" onClick={(event) => event.stopPropagation()}>{sidebar}</div></div>}
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex min-h-[76px] items-center justify-between gap-3 border-b border-slate-800/90 bg-[#080d18]/90 px-4 backdrop-blur-xl md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button onClick={() => setMobileOpen(true)} aria-label="Open navigation" className="rounded-lg border border-slate-700 p-2 text-slate-300 lg:hidden"><Menu size={18} /></button>
            <div className="hidden items-center gap-2 text-xs text-slate-500 md:flex"><Command size={14} /> Operations</div>
            <div className="relative w-[min(42vw,360px)]">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input aria-label="Search navigation" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && filtered[0]) { navigate(filtered[0].to); setSearch('') } }}
                placeholder="Search pages..." className="w-full rounded-xl border border-slate-800 bg-slate-900/70 py-2 pl-9 pr-3 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-500/60" />
              {filtered.length > 0 && <div className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-xl">{filtered.map(({ to, label, icon: Icon }) => <button key={to} onClick={() => { navigate(to); setSearch('') }} className="flex w-full items-center gap-3 px-3 py-3 text-left text-sm text-slate-200 hover:bg-slate-800"><Icon size={16} />{label}</button>)}</div>}
            </div>
          </div>
          <div className="flex items-center gap-2 md:gap-3">
            <StatusChip tone={live === 'connected' ? 'green' : live === 'connecting' ? 'amber' : 'slate'}><span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-current" />{live === 'connected' ? 'Live connected' : live === 'connecting' ? 'Connecting' : 'Offline'}</StatusChip>
            <div className="hidden md:block"><StatusChip tone="amber">Simulated data</StatusChip></div>
            <div className="relative">
              <button onClick={() => setNotificationsOpen((value) => !value)} aria-label="Open notifications" aria-expanded={notificationsOpen} className="relative rounded-xl border border-slate-800 p-2.5 text-slate-300 hover:bg-slate-900"><Bell size={17} />{events.length > 0 && <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-cyan-300" />}</button>
              {notificationsOpen && <div className="absolute right-0 top-full z-50 mt-2 w-[min(90vw,340px)] rounded-2xl border border-slate-700 bg-slate-900 p-3 shadow-2xl"><div className="mb-2 flex items-center justify-between px-1"><strong className="text-sm text-white">Live notifications</strong><button onClick={() => setNotificationsOpen(false)} aria-label="Close notifications"><X size={15} /></button></div>{events.length === 0 ? <p className="p-3 text-sm text-slate-400">No new live notifications.</p> : events.map((event, index) => <div key={`${event}-${index}`} className="border-t border-slate-800 p-3 text-sm text-slate-300">{event}</div>)}</div>}
            </div>
            <div className="relative">
              <button onClick={() => setProfileOpen((value) => !value)} aria-expanded={profileOpen} className="flex items-center gap-2 rounded-xl border border-slate-800 p-1.5 pr-2.5 hover:bg-slate-900">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-500/15 text-xs font-semibold text-cyan-200">{user?.username.slice(0, 2).toUpperCase() ?? 'OP'}</span>
                <span className="hidden max-w-24 truncate text-left text-xs md:block"><span className="block text-slate-200">{user?.username ?? 'Operator'}</span><span className="text-slate-500">{user?.role ?? 'User'}</span></span><ChevronDown size={14} className="text-slate-500" />
              </button>
              {profileOpen && <div className="absolute right-0 top-full z-50 mt-2 w-52 rounded-xl border border-slate-700 bg-slate-900 p-1 shadow-xl"><Link to="/app/profile" onClick={() => setProfileOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-slate-300 hover:bg-slate-800"><UserRound size={15} /> Profile</Link><Link to="/app/settings" onClick={() => setProfileOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-slate-300 hover:bg-slate-800"><Settings size={15} /> Settings</Link><button onClick={() => { setProfileOpen(false); void logout().then(() => navigate('/')).catch(() => { notify('Signed out locally, but server token revocation failed.', 'error'); navigate('/') }) }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-red-300 hover:bg-red-500/10"><LogOut size={15} /> Sign out</button></div>}
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1700px] p-4 md:p-6 xl:p-8"><Outlet /></main>
      </div>
    </div>
  )
}
