import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import ReviewWidget from '../components/ReviewWidget'

// lib/api (axios 인스턴스) mock
vi.mock('../lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

import api from '../lib/api'
const mockApi = api as any

beforeEach(() => { vi.clearAllMocks() })

describe('ReviewWidget', () => {
  it('shows empty state when no reviews', async () => {
    mockApi.get.mockResolvedValue({ data: [] })
    render(<BrowserRouter><ReviewWidget /></BrowserRouter>)
    await waitFor(() => {
      expect(screen.getByText(/오늘 복습할 문제가 없습니다/)).toBeInTheDocument()
    })
  })

  it('shows review cards when items exist', async () => {
    mockApi.get.mockResolvedValue({
      data: [{
        question_id: '01-01:1',
        question_text: 'TCP란 무엇인가요?',
        part: '01-network',
        last_score: 5,
        next_review_at: new Date().toISOString(),
      }],
    })
    render(<BrowserRouter><ReviewWidget /></BrowserRouter>)
    await waitFor(() => {
      expect(screen.getByText(/오늘의 복습/)).toBeInTheDocument()
    })
  })
})
