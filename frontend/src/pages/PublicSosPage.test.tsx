import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider } from '../components/Ui'
import { PublicSosPage } from './Pages'

describe('PublicSosPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: 'sos-test-1', status: 'Pending Approval', created_at: '2026-01-01T00:00:00Z', cancel_token: 'test-cancel-token' }),
    }))
  })

  it('requires explicit second-step confirmation before submitting an SOS', async () => {
    render(<MemoryRouter><ToastProvider><PublicSosPage /></ToastProvider></MemoryRouter>)
    fireEvent.change(screen.getByPlaceholderText('Short description of response need'), { target: { value: 'Synthetic test incident, no patient data.' } })
    fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: '40.7' } })
    fireEvent.change(screen.getByLabelText('Longitude'), { target: { value: '-74.0' } })
    fireEvent.click(screen.getByRole('button', { name: 'Review SOS request' }))

    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Submit SOS' }))

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1))
    expect(localStorage.getItem('resqnet.sos.cancel.sos-test-1')).toBe('test-cancel-token')
  })
})
