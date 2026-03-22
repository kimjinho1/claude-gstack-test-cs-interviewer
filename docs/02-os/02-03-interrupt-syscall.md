# 02-03 인터럽트 / 시스템 콜

## 개념

**인터럽트(Interrupt)**: CPU가 현재 작업을 멈추고 긴급 이벤트를 처리하는 메커니즘.
**시스템 콜(System Call)**: 사용자 프로그램이 OS 커널 기능을 요청하는 인터페이스.

---

## 동작 원리

### CPU 모드: 커널 모드 vs 유저 모드

```
유저 모드 (User Mode):
  - 일반 응용 프로그램 실행
  - 하드웨어 직접 접근 불가
  - 메모리 제한된 영역만 접근

커널 모드 (Kernel Mode):
  - OS 커널 실행
  - 하드웨어 직접 접근 가능
  - 모든 메모리 접근 가능

전환: 유저 → 커널 (시스템 콜, 인터럽트)
      커널 → 유저 (시스템 콜 반환, 인터럽트 처리 완료)
```

보호 링(Protection Ring):
```
Ring 0: 커널 (최고 권한)
Ring 3: 사용자 프로그램 (최소 권한)
```

### 인터럽트 동작 흐름

```
① CPU: 프로세스 A 실행 중
② 인터럽트 발생 (NIC에서 패킷 수신)
③ 현재 실행 중인 명령어 완료
④ 레지스터/PC → 스택에 저장
⑤ IDT(Interrupt Descriptor Table)에서 ISR 주소 조회
⑥ ISR(Interrupt Service Routine) 실행 → 패킷 처리
⑦ 저장했던 레지스터/PC 복원
⑧ 프로세스 A 실행 재개
```

### 인터럽트 종류

| 종류 | 발생 원인 | 예시 |
|------|---------|------|
| 하드웨어 인터럽트 | 외부 장치 | NIC 패킷 수신, 키보드 입력, 타이머 |
| 소프트웨어 인터럽트 | 프로그램 | 시스템 콜 (int 0x80, syscall) |
| 예외 (Exception) | CPU 오류 | 0으로 나누기, 페이지 폴트, Segfault |

**스위치/AP 관점의 인터럽트**
```
NIC 패킷 수신 → 하드웨어 인터럽트 → ISR에서 패킷 처리
포트 link up/down → 인터럽트 → 상태 변경 이벤트 처리
타이머 인터럽트 → 스케줄러 실행 → 다음 프로세스로 전환
```

### 시스템 콜 동작 흐름

사용자 프로그램이 파일 읽기, 소켓 통신, 프로세스 생성 등 커널 기능을 요청할 때.

```
① 사용자 프로그램: read(fd, buf, size) 호출
② 라이브러리(glibc): syscall 번호(3) + 인자를 레지스터에 설정
③ syscall 명령어 실행 → 유저 모드 → 커널 모드 전환
④ 커널: 시스템 콜 테이블에서 sys_read 함수 호출
⑤ 커널: 실제 파일 데이터를 사용자 버퍼에 복사
⑥ 커널 → 유저 모드 전환 후 반환값 전달
⑦ 사용자 프로그램: 결과 사용
```

### 주요 시스템 콜

| 분류 | 시스템 콜 | 역할 |
|------|---------|------|
| 파일 | open, read, write, close | 파일 I/O |
| 프로세스 | fork, exec, exit, wait | 프로세스 관리 |
| 메모리 | mmap, brk | 메모리 할당 |
| 네트워크 | socket, bind, listen, accept, connect, send, recv | 소켓 통신 |
| 신호 | signal, kill | 프로세스 신호 |

### 인터럽트 vs 시스템 콜

```
인터럽트:
  발생: 하드웨어/외부 이벤트 (비동기)
  주체: 장치가 CPU에게 알림
  예:   NIC 패킷 수신

시스템 콜:
  발생: 사용자 프로그램이 명시적으로 요청 (동기)
  주체: 프로그램이 커널에게 요청
  예:   socket(), send(), recv()
```

---

## 예시 코드 (Python)

```python
import os
import socket
import signal
import time


# ── 시스템 콜 추적 ────────────────────────────────────

# Python의 모든 I/O, 네트워크, 파일 작업은 내부적으로 시스템 콜
# strace로 확인 가능: strace python script.py

def demonstrate_syscalls():
    """주요 시스템 콜 Python 레벨 예시"""

    # fork() + exec() → 자식 프로세스 생성
    pid = os.fork()
    if pid == 0:
        # 자식 프로세스
        print(f"[자식] PID={os.getpid()}, 부모PID={os.getppid()}")
        os.execv("/bin/echo", ["echo", "자식 프로세스 exec"])
    else:
        # 부모 프로세스
        print(f"[부모] PID={os.getpid()}, 자식PID={pid}")
        os.waitpid(pid, 0)  # wait() 시스템 콜
        print(f"[부모] 자식 프로세스 완료")


# ── 소켓 시스템 콜 시뮬레이션 ─────────────────────────

def socket_syscalls_demo():
    """
    소켓 통신의 시스템 콜 흐름:
    socket() → bind() → listen() → accept() → read/write → close()
    """
    # socket() 시스템 콜: 소켓 파일 디스크립터 생성
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # bind() 시스템 콜: 주소/포트 바인딩
    server_sock.bind(("127.0.0.1", 9999))

    # listen() 시스템 콜: 연결 대기 큐 설정
    server_sock.listen(5)
    print("[Server] socket() → bind() → listen() 완료")

    server_sock.close()


# ── 시그널(인터럽트 소프트웨어 버전) ────────────────────

def signal_handler(signum, frame):
    """SIGTERM 시그널 핸들러 (스위치 데몬 종료 처리)"""
    print(f"\n[시그널] SIGTERM({signum}) 수신 → 정리 후 종료")
    # 실제 데몬이라면: 소켓 닫기, 상태 저장, 로그 쓰기
    raise SystemExit(0)


signal.signal(signal.SIGTERM, signal_handler)  # signal() 시스템 콜


# ── 인터럽트 기반 I/O (select/epoll) ─────────────────

import select


def interrupt_driven_io():
    """
    select()로 여러 소켓을 동시에 모니터링 (I/O 멀티플렉싱)
    스위치 데몬이 여러 연결을 동시에 처리하는 방식

    내부적으로 select/poll/epoll 시스템 콜 사용
    소켓에 데이터 도착 → 인터럽트 → OS가 프로세스 깨움
    """
    socks = []
    for port in range(10000, 10004):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            s.listen(1)
            socks.append(s)
        except:
            pass

    print(f"[I/O 멀티플렉싱] {len(socks)}개 소켓 모니터링 중...")

    # select()로 읽기 가능한 소켓 대기 (타임아웃 1초)
    readable, _, _ = select.select(socks, [], [], 1.0)

    if readable:
        print(f"[I/O] {len(readable)}개 소켓에 이벤트")
    else:
        print("[I/O] 타임아웃 (연결 없음)")

    for s in socks:
        s.close()


socket_syscalls_demo()
interrupt_driven_io()
```

---

## 면접 예상 질문

- Q: 인터럽트란 무엇이고 왜 필요한가?
  A: CPU가 현재 작업을 멈추고 긴급 이벤트를 처리하는 메커니즘. Polling(주기적 확인) 없이 이벤트 발생 즉시 처리 가능해 CPU를 효율적으로 사용. 스위치에서 패킷 수신, 포트 상태 변경 등을 인터럽트로 처리.

- Q: 시스템 콜이란? 왜 유저 모드에서 직접 하드웨어에 접근 못 하나?
  A: 사용자 프로그램이 OS 커널 기능(파일, 네트워크, 프로세스 생성 등)을 요청하는 인터페이스. 유저 모드에서 하드웨어에 직접 접근을 허용하면 악성 프로그램이 다른 프로세스 메모리 읽기, 하드웨어 조작 등 보안 침해 가능. 커널 모드에서만 접근하게 해 OS가 제어.

- Q: 하드웨어 인터럽트와 소프트웨어 인터럽트(시스템 콜)의 차이는?
  A: 하드웨어 인터럽트는 외부 장치가 비동기적으로 CPU에 알림 (NIC 패킷 수신, 타이머). 소프트웨어 인터럽트(시스템 콜)는 실행 중인 프로그램이 명시적으로 커널에 서비스를 요청 (동기). 둘 다 유저→커널 모드 전환을 유발.

- Q: 인터럽트 처리 중 또 다른 인터럽트가 오면?
  A: 인터럽트 우선순위에 따라 처리. 높은 우선순위 인터럽트는 현재 ISR을 중단하고 먼저 처리(Nested Interrupt). 낮은 우선순위는 현재 ISR 완료 후 처리. 인터럽트 마스킹으로 특정 인터럽트를 임시 비활성화 가능.

---

## 관련 개념

- [02-01 프로세스 vs 스레드](./02-01-process-thread.md) — 인터럽트가 Context Switch 유발
- [02-04 CPU 스케줄링](./02-04-cpu-scheduling.md) — 타이머 인터럽트로 스케줄러 실행
