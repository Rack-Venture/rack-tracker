# 팀 온보딩 가이드

이 문서는 레포를 포크한 뒤 로컬 개발 환경을 처음 세팅할 때 참고한다.

---

## 사전 설치

아래 세 가지만 먼저 설치한다.

| 도구 | 역할 | 설치 링크 |
|------|------|-----------|
| **Node.js** (18+ LTS) | 프론트엔드 실행 | https://nodejs.org |
| **uv** | 백엔드 Python 환경 관리 | https://docs.astral.sh/uv/getting-started/installation/ |
| **GitHub CLI (`gh`)** | 이슈·PR 관리 | https://cli.github.com |

> Python은 따로 설치하지 않아도 된다. `uv`가 `.python-version`(3.12)을 읽어 자동으로 설치한다.

---

## 레포 포크 및 클론

```bash
# GitHub에서 포크한 뒤
git clone https://github.com/<내-계정>/rack-tracker.git
cd rack-tracker
```

---

## 프론트엔드 (`frontend/`)

```bash
cd frontend
npm install
```

> **주의:** `npm install`을 먼저 실행하지 않으면 `npm run dev` 시 `'vite' is not recognized` 오류가 난다.

환경변수 파일을 생성한다 (`.env.local`은 git에서 관리되지 않는다):

```bash
cp .env.local.example .env.local
```

실행:

```bash
npm run dev
# → http://localhost:5173
```

---

## 백엔드 (`backend/`)

```bash
cd backend
uv sync                  # Python 3.12 + 의존성 자동 설치
cp .env.example .env     # 환경변수 파일 생성
```

`.env`를 열고 `ANTHROPIC_API_KEY`를 채운다 (LLM 피드백 기능에 필요):

```
HOST=127.0.0.1
PORT=8000

ANTHROPIC_API_KEY=sk-ant-...   # ← 개인 키 입력
LLM_FEEDBACK_MODEL=claude-sonnet-4-6
```

실행:

```bash
uv run main.py
# → http://127.0.0.1:8000
```

서버가 켜지면 브라우저에서 `http://127.0.0.1:8000/` 접속 시 아래 응답이 보인다:

```json
{"message": "Motion Analysis Backend is running."}
```

---

## 데이터 파일 다운로드

대용량 파일(캘리브레이션 JSON, 영상 등)은 git에 포함되지 않는다.  
아래 스크립트로 Google Drive에서 받는다:

```bash
python scripts/download_data.py
```

파일이 이미 있으면 건너뛴다. 강제 재다운로드는 `--force` 옵션을 붙인다.

---

## Agent 워크플로우

Claude Code를 사용하는 팀원은 아래 순서로 문서를 읽는다:

1. `AGENTS.md` — 세션 시작 시 반드시 읽는다
2. `docs/agent-workflow/README.md` — 워크플로우 전체 구조
3. `docs/agent-workflow/git-rules.md` — 브랜치·커밋·PR 규칙
4. `docs/agent-workflow/documentation-rules.md` — 작업 로그 규칙

작업 추적 문서는 `docs/issues/` 아래에 있다.

---

## GitHub 워크플로우

현재 CI/CD 파이프라인은 구성되어 있지 않다.  
테스트와 빌드 확인은 로컬에서 직접 실행한다.

---

## 포트 정리

| 서비스 | 주소 |
|--------|------|
| 프론트엔드 (Vite) | http://localhost:5173 |
| 백엔드 (FastAPI) | http://127.0.0.1:8000 |

프론트엔드 `VITE_API_BASE_URL`과 백엔드 `PORT`는 **8000으로 통일**되어 있다.

---

## 세팅 완료 체크리스트

- [ ] Node.js, uv, gh 설치 완료
- [ ] `frontend/npm install` 완료
- [ ] `backend/uv sync` 완료
- [ ] `backend/.env`에 `ANTHROPIC_API_KEY` 입력
- [ ] `python scripts/download_data.py` 실행
- [ ] 프론트엔드 `http://localhost:5173` 접속 확인
- [ ] 백엔드 `http://127.0.0.1:8000/` 접속 확인
