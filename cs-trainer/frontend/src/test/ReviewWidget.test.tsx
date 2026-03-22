import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import ReviewWidget from '../components/ReviewWidget'
import axios from 'axios'

vi.mock('axios')
const mockAxios = axios as any

beforeEach(() => { vi.clearAllMocks() })

describe('ReviewWidget', () => {
  it('shows empty state when no reviews', async () => {
    mockAxios.get = vi.fn().mockResolvedValue({ data: [] })
    render(<BrowserRouter><ReviewWidget /></BrowserRouter>)
    await waitFor(() => {
      expect(screen.getByText(/오늘 복습할 문제가 없습니다/)).toBeInTheDocument()
    })
  })

  it('shows review cards when items exist', async () => {
    mockAxios.get = vi.fn().mockResolvedValue({
      data: [{ question_id: '01-01:1', question_text: 'TCP란 무엇인가요?', part: '01-network', last_score: 5, next_review_at: new Date().toISOString() }]
    })
    render(<BrowserRouter><ReviewWidget /></BrowserRouter>)
    await waitFor(() => {
      expect(screen.getByText(/오늘의 복습/)).toBeInTheDocument()
    })
  })
})
