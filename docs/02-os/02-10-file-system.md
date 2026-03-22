# 02-10 파일 시스템

## 개념

OS가 디스크(저장 장치)의 데이터를 **파일/디렉토리** 형태로 구성하고 관리하는 시스템.

```
사용자: open("config.json"), read(), write()
파일 시스템: 논리 파일 ↔ 물리 디스크 블록 매핑
디스크: 0/1 비트의 연속된 저장 공간
```

---

## 동작 원리

### 디스크 구조

```
디스크 기본 단위: 섹터 (512B 또는 4KB)
파일 시스템 단위: 블록 (4KB, 여러 섹터 묶음)

파티션 레이아웃 (ext4 기준):
┌─────────┬────────────┬──────────┬───────────────────────┐
│ Boot    │ Super Block│ Inode    │ Data Blocks           │
│ 블록    │ (FS 메타)  │ Table    │ (실제 파일 데이터)    │
└─────────┴────────────┴──────────┴───────────────────────┘
```

### Inode (색인 노드)

파일의 **메타데이터 + 데이터 블록 위치** 저장. 파일명은 없음.

```
Inode 구조:
  - 파일 크기
  - 소유자 (UID, GID)
  - 권한 (rwxr-xr--)
  - 타임스탬프 (생성/수정/접근)
  - 링크 카운트
  - 데이터 블록 포인터:
      직접 포인터 12개 (작은 파일: 12 × 4KB = 48KB)
      간접 포인터 (Indirect): 포인터 블록 → 데이터
      이중 간접 (Double Indirect)
      삼중 간접 (Triple Indirect)

디렉토리 = 파일명 → Inode 번호 매핑 테이블
```

**파일 열기 흐름**:

```
open("/etc/config.json")

① 경로 파싱: "/" → "etc" → "config.json"
② 루트 inode(#2) 로드
③ 루트 디렉토리 data block에서 "etc" 검색 → inode #53
④ inode #53 로드 (etc 디렉토리)
⑤ etc 디렉토리 data block에서 "config.json" 검색 → inode #1024
⑥ inode #1024 로드 → 파일 메타데이터, 데이터 블록 위치 획득
⑦ 파일 디스크립터(fd) 반환

read(fd, buf, size):
  inode #1024의 데이터 블록 포인터 → 디스크 읽기 → 버퍼 복사
```

### 파일 디스크립터 (File Descriptor)

```
프로세스별 파일 디스크립터 테이블:
  fd 0: stdin
  fd 1: stdout
  fd 2: stderr
  fd 3: 열린 파일 A
  fd 4: 소켓 B

open() → fd 번호 반환
read(fd, ...) / write(fd, ...) / close(fd)

커널 내부:
  fd → 파일 테이블 엔트리 (offset, 플래그) → inode
```

### 주요 파일 시스템

| 파일 시스템 | OS | 특징 |
|-----------|----|----|
| **ext4** | Linux | 저널링, 안정적, 대용량 지원 |
| **XFS** | Linux | 대용량 파일, 병렬 I/O 우수 |
| **NTFS** | Windows | 저널링, ACL, 압축/암호화 |
| **APFS** | macOS | SSD 최적화, CoW, 스냅샷 |
| **FAT32** | 범용 | 단순, 하위 호환, 4GB 파일 제한 |
| **tmpfs** | Linux | RAM 기반, 재부팅 시 소멸 |

### 저널링 (Journaling)

```
문제: 파일 쓰기 중 전원 차단 → 파일 시스템 손상

저널링: 실제 변경 전 저널(로그)에 먼저 기록
  ① 저널에 "할 작업" 기록
  ② 실제 데이터/메타데이터 변경
  ③ 저널 커밋 완료 표시

재부팅 시: 저널 확인 → 미완료 작업 재실행 또는 롤백
→ ext4, NTFS, APFS 모두 저널링 사용
```

### VFS (Virtual File System)

```
Linux의 파일 시스템 추상화 계층

애플리케이션
    ↓ open(), read(), write()
   VFS (가상 파일 시스템)
    ↓
ext4 | XFS | tmpfs | NFS | procfs ...

→ 앱은 실제 파일 시스템 종류를 몰라도 됨
→ 네트워크 파일 시스템(NFS), 가상 파일 시스템(procfs)도 동일 인터페이스
```

### 링크 (Hard Link / Soft Link)

```
Hard Link: 같은 inode를 가리키는 다른 파일명
  ln file.txt hard_link.txt
  → inode 링크 카운트: 2
  → 원본 삭제해도 링크 유효 (카운트 1이 되면 inode 존재)
  → 다른 파일 시스템 파티션 간 불가

Symbolic Link (Soft Link): 경로를 저장하는 특수 파일
  ln -s file.txt soft_link.txt
  → 원본 삭제 시 링크 깨짐 (dangling link)
  → 다른 파티션, 디렉토리 가능
```

---

## 예시 코드 (Python)

```python
import os
import stat
import time
from pathlib import Path


# ── 파일 메타데이터 (inode 정보) ───────────────────────

def show_inode_info(path: str):
    """파일의 inode 정보 출력"""
    info = os.stat(path)
    print(f"\n[{path}] inode 정보:")
    print(f"  inode 번호:   {info.st_ino}")
    print(f"  파일 크기:    {info.st_size} bytes")
    print(f"  하드 링크 수: {info.st_nlink}")
    print(f"  권한:         {oct(info.st_mode)[-4:]}")
    print(f"  소유자 UID:   {info.st_uid}")
    print(f"  수정 시간:    {time.ctime(info.st_mtime)}")
    print(f"  블록 수:      {info.st_blocks}")


# ── 파일 디스크립터와 저수준 I/O ──────────────────────

def low_level_io_demo():
    """os.open/read/write: 시스템 콜 수준 파일 I/O"""
    tmp = "/tmp/fd_demo.txt"

    # open() 시스템 콜: fd 반환
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    print(f"\nopen() → fd={fd}")

    # write() 시스템 콜
    data = b"switch config backup\n" * 3
    written = os.write(fd, data)
    print(f"write() → {written} bytes 기록")
    os.close(fd)

    # read() 시스템 콜
    fd = os.open(tmp, os.O_RDONLY)
    content = os.read(fd, 1024)
    print(f"read()  → {len(content)} bytes 읽음")
    os.close(fd)
    os.unlink(tmp)


# ── 디렉토리 순회: inode 연결 흐름 ────────────────────

def walk_demo(root: str = "/tmp"):
    """경로 → inode 번호 출력"""
    print(f"\n[디렉토리 탐색: {root}]")
    for entry in os.scandir(root):
        try:
            info = entry.stat(follow_symlinks=False)
            ftype = "DIR " if entry.is_dir() else "FILE"
            link  = " → " + os.readlink(entry.path) if entry.is_symlink() else ""
            print(f"  {ftype} inode={info.st_ino:<8} {entry.name}{link}")
        except PermissionError:
            pass


# ── 간단한 파일 시스템 시뮬레이션 ─────────────────────

class SimpleFS:
    """
    메모리 기반 간이 파일 시스템
    inode + 데이터 블록 + 디렉토리 구조 시뮬레이션
    """
    BLOCK_SIZE = 4096

    def __init__(self):
        self._inodes: dict[int, dict] = {}  # inode_no → metadata
        self._blocks: dict[int, bytes] = {} # block_no → data
        self._dirs:   dict[int, dict] = {}  # inode_no → {name: inode_no}
        self._next_inode = 1
        self._next_block = 0

        # 루트 디렉토리 생성
        root_inode = self._alloc_inode("dir")
        self._dirs[root_inode] = {}
        print(f"루트 디렉토리: inode #{root_inode}")
        self._root = root_inode

    def _alloc_inode(self, ftype: str) -> int:
        no = self._next_inode
        self._inodes[no] = {
            "type": ftype,
            "size": 0,
            "nlink": 1,
            "blocks": [],
            "ctime": time.time(),
        }
        self._next_inode += 1
        return no

    def _alloc_block(self, data: bytes) -> int:
        no = self._next_block
        self._blocks[no] = data.ljust(self.BLOCK_SIZE, b'\x00')
        self._next_block += 1
        return no

    def create(self, parent_inode: int, name: str, content: bytes) -> int:
        """파일 생성"""
        inode = self._alloc_inode("file")
        block = self._alloc_block(content)
        self._inodes[inode]["blocks"].append(block)
        self._inodes[inode]["size"] = len(content)
        self._dirs[parent_inode][name] = inode
        print(f"  create '{name}' → inode #{inode}, block #{block}, {len(content)} bytes")
        return inode

    def read(self, inode_no: int) -> bytes:
        """파일 읽기"""
        inode = self._inodes[inode_no]
        result = b""
        for block_no in inode["blocks"]:
            result += self._blocks[block_no][:inode["size"]]
        return result

    def lookup(self, parent_inode: int, name: str) -> int:
        """디렉토리에서 파일 찾기"""
        return self._dirs[parent_inode].get(name, -1)

    def ls(self, inode_no: int):
        """디렉토리 목록"""
        print(f"  ls (inode #{inode_no}):")
        for name, ino in self._dirs.get(inode_no, {}).items():
            meta = self._inodes[ino]
            print(f"    {name:20s} inode={ino} size={meta['size']}")


print("=== inode 정보 ===")
# 실제 파일 정보
show_inode_info(__file__ if os.path.exists(__file__) else "/etc/hosts")

print("\n=== 저수준 파일 I/O ===")
low_level_io_demo()

print("\n=== 간이 파일 시스템 시뮬레이션 ===")
fs = SimpleFS()
fs.create(fs._root, "config.json", b'{"vlan": 10, "port": 443}')
fs.create(fs._root, "backup.tar",  b"binary backup data" * 10)
fs.ls(fs._root)

# 파일 읽기
ino = fs.lookup(fs._root, "config.json")
data = fs.read(ino)
print(f"\n  config.json 내용: {data.rstrip(b\"\\x00\")}")

print("\n=== 디렉토리 탐색 ===")
walk_demo("/tmp")
```

---

## 면접 예상 질문

- Q: inode란 무엇인가?
  A: 파일의 메타데이터(크기, 권한, 소유자, 타임스탬프)와 데이터 블록 포인터를 저장하는 자료구조. 파일명은 디렉토리에 저장되고, 파일명 → inode 번호로 연결. 하드 링크는 같은 inode를 가리키는 다른 파일명. `ls -i`로 inode 번호 확인 가능.

- Q: 파일 open() → read() 흐름을 설명하라.
  A: open()에서 경로를 파싱해 각 디렉토리의 inode를 순서대로 탐색, 최종 파일 inode를 찾아 파일 디스크립터(fd) 반환. read(fd)에서 fd → 파일 테이블 엔트리 → inode → 데이터 블록 주소 → 디스크 읽기 → 사용자 버퍼 복사.

- Q: 저널링(Journaling)이란?
  A: 파일 시스템 변경 전 저널(로그)에 먼저 기록해 시스템 장애 시 복구를 보장하는 기법. 변경 작업을 원자적으로 처리 — 완전히 성공하거나 실패 시 롤백. ext4, NTFS, APFS 등 현대 파일 시스템이 사용. 파일 시스템 fsck(점검) 시간 대폭 단축.

- Q: Hard Link와 Symbolic Link의 차이는?
  A: Hard Link는 같은 inode를 가리키는 추가 파일명. 원본 삭제해도 데이터 유지(링크 카운트가 0이 될 때 삭제). 파티션 간 불가. Symbolic Link는 대상 경로를 저장하는 특수 파일. 원본 삭제 시 링크 깨짐. 파티션 간, 디렉토리도 가능. `ls -l`에서 `->` 표시.

---

## 관련 개념

- [02-03 인터럽트 / 시스템 콜](./02-03-interrupt-syscall.md) — open/read/write 시스템 콜
- [02-07 메모리 관리](./02-07-memory-management.md) — 파일 페이지 캐시 (Page Cache)
- [02-08 가상 메모리](./02-08-virtual-memory.md) — mmap() 파일 매핑
