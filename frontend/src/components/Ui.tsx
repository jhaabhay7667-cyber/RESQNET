import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, Check, LoaderCircle, X } from 'lucide-react'
import { Component, createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

type ToastTone = 'success' | 'error' | 'info'
type ToastMessage = { id: number; message: string; tone: ToastTone }
type ToastContextValue = { notify: (message: string, tone?: ToastTone) => void }

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([])
  const notify = useCallback((message: string, tone: ToastTone = 'info') => {
    const id = Date.now() + Math.random()
    setMessages((items) => [...items, { id, message, tone }])
    window.setTimeout(() => setMessages((items) => items.filter((item) => item.id !== id)), 4500)
  }, [])
  const value = useMemo(() => ({ notify }), [notify])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[2000] flex w-[min(92vw,380px)] flex-col gap-2" aria-live="polite">
        <AnimatePresence>
          {messages.map((item) => (
            <motion.div key={item.id} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 16 }}
              className={`flex items-center gap-3 rounded-xl border p-3 shadow-xl ${item.tone === 'error' ? 'border-red-500/30 bg-red-950 text-red-100' : item.tone === 'success' ? 'border-emerald-500/30 bg-emerald-950 text-emerald-100' : 'border-slate-700 bg-slate-900 text-slate-100'}`}>
              {item.tone === 'success' ? <Check size={17} /> : <AlertCircle size={17} />}
              <span className="flex-1 text-sm">{item.message}</span>
              <button aria-label="Dismiss notification" onClick={() => setMessages((items) => items.filter((entry) => entry.id !== item.id))}><X size={15} /></button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const value = useContext(ToastContext)
  if (!value) throw new Error('useToast must be used within ToastProvider')
  return value
}

export function PageTitle({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <div className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-tight text-white md:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-sm text-slate-400">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-slate-800 bg-[#111827]/90 p-5 shadow-xl shadow-black/10 ${className}`}>{children}</section>
}

export function Button({ children, variant = 'primary', className = '', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'danger' }) {
  const styles = variant === 'primary'
    ? 'bg-cyan-400 text-slate-950 hover:bg-cyan-300'
    : variant === 'danger'
      ? 'border border-red-500/30 bg-red-500/10 text-red-200 hover:bg-red-500/20'
      : 'border border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500'
  return <button {...props} className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}>{props.disabled ? <LoaderCircle className="animate-spin" size={16} /> : null}{children}</button>
}

export function Field({ label, hint, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className="block text-sm text-slate-300">
      <span className="mb-1.5 block">{label}</span>
      <input {...props} className={`w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-cyan-400 ${props.className ?? ''}`} />
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  )
}

export function SelectField({ label, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm text-slate-300">
      <span className="mb-1.5 block">{label}</span>
      <select {...props} className={`w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-slate-100 outline-none focus:border-cyan-400 ${props.className ?? ''}`}>{children}</select>
    </label>
  )
}

export function TextAreaField({ label, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className="block text-sm text-slate-300">
      <span className="mb-1.5 block">{label}</span>
      <textarea {...props} className={`w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-400 ${props.className ?? ''}`} />
    </label>
  )
}

export function StatusChip({ children, tone = 'slate' }: { children: ReactNode; tone?: 'red' | 'amber' | 'green' | 'cyan' | 'slate' }) {
  const tones = { red: 'border-red-500/20 bg-red-500/10 text-red-300', amber: 'border-amber-500/20 bg-amber-500/10 text-amber-200', green: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300', cyan: 'border-cyan-500/20 bg-cyan-500/10 text-cyan-200', slate: 'border-slate-700 bg-slate-800/70 text-slate-300' }
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs ${tones[tone]}`}>{children}</span>
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-800 ${className}`} aria-label="Loading" />
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-slate-700 px-5 py-12 text-center"><h3 className="font-medium text-white">{title}</h3><p className="mx-auto mt-2 max-w-md text-sm text-slate-400">{description}</p>{action && <div className="mt-4">{action}</div>}</div>
}

export function ConfirmDialog({ title, description, onConfirm, onCancel, confirmText = 'Confirm', children }: { title: string; description: string; onConfirm: () => void; onCancel: () => void; confirmText?: string; children?: ReactNode }) {
  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-black/70 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel() }}>
      <div role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <h2 id="confirm-title" className="text-lg font-semibold text-white">{title}</h2>
        <p className="mt-2 text-sm text-slate-400">{description}</p>
        {children && <div className="mt-4">{children}</div>}
        <div className="mt-6 flex justify-end gap-3"><Button variant="secondary" onClick={onCancel}>Cancel</Button><Button onClick={onConfirm}>{confirmText}</Button></div>
      </div>
    </div>
  )
}

export class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  render() {
    if (this.state.hasError) return <div className="m-8 rounded-2xl border border-red-500/30 bg-red-950/30 p-6 text-red-100" role="alert"><h1 className="text-lg font-semibold">This screen could not be displayed</h1><p className="mt-2 text-sm text-red-200">Reload the page or return to the command center.</p><a className="mt-4 inline-block underline" href="/app/dashboard">Command center</a></div>
    return this.props.children
  }
}
