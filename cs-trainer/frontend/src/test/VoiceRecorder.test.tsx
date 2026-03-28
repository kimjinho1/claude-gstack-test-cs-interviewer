import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import VoiceRecorder from '../components/VoiceRecorder'

// useSpeechRecognition mock
const mockStart = vi.fn()
const mockStop = vi.fn()
const mockReset = vi.fn()
let mockTranscript = ''
let mockIsListening = false
let mockIsSupported = true

vi.mock('../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: () => ({
    transcript: mockTranscript,
    isListening: mockIsListening,
    isSupported: mockIsSupported,
    start: mockStart,
    stop: mockStop,
    reset: mockReset,
  }),
}))

beforeEach(() => {
  vi.clearAllMocks()
  mockTranscript = ''
  mockIsListening = false
  mockIsSupported = true
})

describe('VoiceRecorder', () => {
  describe('기본 렌더링', () => {
    it('textarea가 항상 표시된다', () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('음성 지원 시 녹음 버튼이 표시된다', () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      expect(screen.getByText('🎙 녹음 시작')).toBeInTheDocument()
    })

    it('음성 미지원 시 경고 메시지가 표시된다', () => {
      mockIsSupported = false
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      expect(screen.getByText(/브라우저가 음성 인식을 지원하지 않아/)).toBeInTheDocument()
      expect(screen.queryByText('🎙 녹음 시작')).not.toBeInTheDocument()
    })

    it('초기에는 초기화 버튼이 없다', () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      expect(screen.queryByText('초기화')).not.toBeInTheDocument()
    })

    it('초기에 제출 버튼은 비활성화 상태', () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      expect(screen.getByText('제출')).toBeDisabled()
    })
  })

  describe('텍스트 직접 입력', () => {
    it('타이핑하면 textarea에 반영된다', async () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      const textarea = screen.getByRole('textbox')
      await userEvent.type(textarea, 'TCP는 연결형 프로토콜')
      expect(textarea).toHaveValue('TCP는 연결형 프로토콜')
    })

    it('텍스트 입력 시 제출 버튼이 활성화된다', async () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      await userEvent.type(screen.getByRole('textbox'), '답변')
      expect(screen.getByText('제출')).not.toBeDisabled()
    })

    it('텍스트 입력 시 초기화 버튼이 나타난다', async () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      await userEvent.type(screen.getByRole('textbox'), '답변')
      expect(screen.getByText('초기화')).toBeInTheDocument()
    })

    it('제출 버튼 클릭 시 onSubmit이 텍스트와 함께 호출된다', async () => {
      const onSubmit = vi.fn()
      render(<VoiceRecorder onSubmit={onSubmit} />)
      await userEvent.type(screen.getByRole('textbox'), '내 답변')
      fireEvent.click(screen.getByText('제출'))
      expect(onSubmit).toHaveBeenCalledWith('내 답변')
    })

    it('공백만 있을 때 제출하면 onSubmit이 호출되지 않는다', async () => {
      const onSubmit = vi.fn()
      render(<VoiceRecorder onSubmit={onSubmit} />)
      await userEvent.type(screen.getByRole('textbox'), '   ')
      fireEvent.click(screen.getByText('제출'))
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('제출 후 textarea가 초기화된다', async () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      const textarea = screen.getByRole('textbox')
      await userEvent.type(textarea, '답변')
      fireEvent.click(screen.getByText('제출'))
      expect(textarea).toHaveValue('')
    })
  })

  describe('Ctrl+Enter 단축키', () => {
    it('Ctrl+Enter로 제출된다', async () => {
      const onSubmit = vi.fn()
      render(<VoiceRecorder onSubmit={onSubmit} />)
      const textarea = screen.getByRole('textbox')
      await userEvent.type(textarea, '단축키 제출')
      fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true })
      expect(onSubmit).toHaveBeenCalledWith('단축키 제출')
    })

    it('Enter 단독으로는 제출되지 않는다', async () => {
      const onSubmit = vi.fn()
      render(<VoiceRecorder onSubmit={onSubmit} />)
      const textarea = screen.getByRole('textbox')
      await userEvent.type(textarea, '단독 엔터')
      fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: false })
      expect(onSubmit).not.toHaveBeenCalled()
    })
  })

  describe('초기화', () => {
    it('초기화 버튼 클릭 시 textarea가 비워진다', async () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      const textarea = screen.getByRole('textbox')
      await userEvent.type(textarea, '지울 내용')
      fireEvent.click(screen.getByText('초기화'))
      expect(textarea).toHaveValue('')
    })

    it('초기화 후 초기화 버튼이 사라진다', async () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      await userEvent.type(screen.getByRole('textbox'), '내용')
      fireEvent.click(screen.getByText('초기화'))
      expect(screen.queryByText('초기화')).not.toBeInTheDocument()
    })

    it('초기화 시 reset hook이 호출된다', async () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      await userEvent.type(screen.getByRole('textbox'), '내용')
      fireEvent.click(screen.getByText('초기화'))
      expect(mockReset).toHaveBeenCalled()
    })
  })

  describe('음성 녹음 연동', () => {
    it('녹음 시작 버튼 클릭 시 start가 호출된다', () => {
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      fireEvent.click(screen.getByText('🎙 녹음 시작'))
      expect(mockStart).toHaveBeenCalled()
    })

    it('녹음 중일 때 버튼 텍스트가 바뀐다', () => {
      mockIsListening = true
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      expect(screen.getByText('🎙 녹음 중지')).toBeInTheDocument()
    })

    it('녹음 중지 버튼 클릭 시 stop이 호출된다', () => {
      mockIsListening = true
      render(<VoiceRecorder onSubmit={vi.fn()} />)
      fireEvent.click(screen.getByText('🎙 녹음 중지'))
      expect(mockStop).toHaveBeenCalled()
    })
  })

  describe('disabled 상태', () => {
    it('disabled=true 시 textarea가 비활성화된다', () => {
      render(<VoiceRecorder onSubmit={vi.fn()} disabled={true} />)
      expect(screen.getByRole('textbox')).toBeDisabled()
    })

    it('disabled=true 시 제출 버튼이 비활성화된다', () => {
      render(<VoiceRecorder onSubmit={vi.fn()} disabled={true} />)
      expect(screen.getByText('제출')).toBeDisabled()
    })

    it('disabled=true 시 녹음 버튼이 비활성화된다', () => {
      render(<VoiceRecorder onSubmit={vi.fn()} disabled={true} />)
      expect(screen.getByText('🎙 녹음 시작')).toBeDisabled()
    })
  })
})
