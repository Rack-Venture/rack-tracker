# RackTracker Backend

> FastAPI 기반 동작 분석 백엔드. Python 3.12 + uv. MediaPipe PoseLandmarker로 포즈를 추정하고, 2-카메라 streaming synthesis로 3D 스켈레톤을 만든 뒤, 운동역학 분석과 LLM 피드백까지 한 파이프라인에서 처리한다.

> ℹ️ 본 저장소(`Rack-Venture/rack-tracker`)는 **창업경진대회 출전용 상업 버전**이다. 자매 저장소 `rack-labs/rack-tracker`(졸업 프로젝트 전용)와 백엔드 코드 구조는 동일하다. 두 저장소의 운영 차이는 루트 [`README.md`](../README.md)의 제품 정체성 섹션을 본다.

저장소 전체 맥락(제품 정체성·로드맵·프론트엔드)은 루트 [`README.md`](../README.md)를 본다. 이 문서는 **백엔드 디렉터리 한정**의 입문·운영 가이드다.

---

## 목차

1. [한눈에 보기](#한눈에-보기)
2. [실행 절차](#실행-절차)
3. [환경 변수](#환경-변수)
4. [6-Layer 아키텍처](#6-layer-아키텍처)
5. [HTTP 라우터](#http-라우터)
6. [비동기 Job 파이프라인](#비동기-job-파이프라인)
7. [데이터 계약](#데이터-계약)
8. [부속 디렉터리](#부속-디렉터리)
9. [폴더 읽는 순서](#폴더-읽는-순서)
10. [데이터 분석 담당자 안내](#데이터-분석-담당자-안내)
11. [관련 문서](#관련-문서)

---

## 한눈에 보기

| 항목 | 값 |
| --- | --- |
| 언어 / 런타임 | Python 3.12 |
| 패키지 매니저 | uv (`pyproject.toml` + `uv.lock`) |
| 웹 프레임워크 | FastAPI + uvicorn |
| 추론 엔진 | MediaPipe PoseLandmarker (Vision API) |
| 영상 I/O | OpenCV |
| LLM | Anthropic Claude (API) |
| 기본 dev URL | `http://127.0.0.1:8000` |
| 프론트엔드 CORS | `http://localhost:5173`, `http://localhost:5174` |
| 테스트 | pytest (`tests/`) |

---

## 실행 절차

```bash
# 1) 의존성 설치 (처음 한 번, 또는 의존성이 바뀐 뒤)
uv sync

# 2) 환경 변수 준비
cp .env.example .env
# .env의 ANTHROPIC_API_KEY 등 비밀 키 채우기

# 3) 서버 실행
uv run main.py
```

서버가 정상 실행되면 `http://127.0.0.1:8000/`에 다음과 같은 응답이 뜬다.

```json
{ "message": "Motion Analysis Backend is running." }
```

테스트 실행:

```bash
uv run pytest
```

> uv는 `uv sync`/`uv run` 호출 시 필요한 가상환경을 자동 구성한다. 별도로 venv를 활성화할 필요는 없다.

신규 팀원의 전체 셋업(Node.js · uv · GitHub CLI 사전 설치, fork·clone, MediaPipe 모델 다운로드 등)은 [`docs/onboarding.md`](../docs/onboarding.md)를 따른다.

---

## 환경 변수

`.env.example`을 그대로 복사한 뒤 키를 채운다. 주요 변수:

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — (필수) | LLM 피드백 생성용 Claude API 키. |
| `POSE_MODEL_DIR` | `models/mediapipe/` | MediaPipe PoseLandmarker `.task` 모델 디렉터리. 외부 경로에 둘 경우 지정. |
| `RELOAD` | `false` | `true`로 두면 uvicorn hot reload. dev에서만 사용. |

> MediaPipe 모델(`.task`)은 git에 포함되지 않는다. 모델 다운로드 절차는 `docs/onboarding.md`에 안내되어 있다.

---

## 6-Layer 아키텍처

요청은 위에서 아래로 흐른다. Service만이 핵심 비즈니스 로직을 담고, Adapter만이 외부 라이브러리를 직접 만진다.

| Layer | 경로 | 역할 |
| --- | --- | --- |
| **Entry** | `main.py` | uvicorn 진입점. `RELOAD` 토글. |
| **App** | `app.py` | FastAPI 앱 조립. GZip · CORS · 라우터 등록. |
| **Controller** | `controller/` | HTTP 라우터. 파싱·직렬화만 담당. |
| **Service** | `service/` | 모든 핵심 로직(추론·합성·분석·피드백·job 관리). |
| **Adapter** | `adapter/` | OpenCV · MediaPipe 외부 경계 격리. |
| **Schema** | `schema/` | Pydantic 모델, 요청·응답 직렬화. |

이 6개 폴더가 백엔드 코드의 골격이다. 새 코드를 어디에 둘지 헷갈리면 위 표 기준으로 판단한다.

---

## HTTP 라우터

| Router | Prefix | 주요 엔드포인트 |
| --- | --- | --- |
| `controller/health.py` | `/` | `GET /` — 헬스 체크. |
| `controller/jobs.py` | `/jobs` | `POST /jobs` *(deprecated, `/synthesis/jobs`로 대체)*, `GET /jobs/{id}`, `GET /jobs/{id}/stream` (SSE). |
| `controller/results.py` | `/jobs` | `GET /jobs/{id}/result`, `GET /jobs/{id}/skeleton{,/download}`, `GET /jobs/{id}/benchmark{,/frames}`. |
| `controller/analysis.py` | `/analysis` | `POST /analysis/preview` — 동기 즉시 분석(샘플 비디오 대체 가능). |
| `controller/synthesis.py` | `/synthesis` | `POST /synthesis/upload`, `POST /synthesis/jobs`, `GET /synthesis/jobs/{id}{,/result}`, `GET /synthesis/jobs/{id}/skeleton3d{,/all}`, `GET /synthesis/jobs/{id}/skeleton_a`. **2-카메라 streaming 합성 파이프라인의 진입점.** |
| `controller/rack_motion.py` | `/rack-motion` | `GET /rack-motion/fixtures/stage1`, `GET /rack-motion/from-synthesis/{id}/stage1`. 3D 스켈레톤 → Stage1 랙 모션 fixture. |

> 신규 클라이언트는 `/synthesis/jobs` 흐름을 사용한다. `/jobs`는 2D 단일 영상 호환 경로로 단계적 통합 중이다.

---

## 비동기 Job 파이프라인

영상 처리는 단일 요청-응답으로 끝낼 수 없어 두 가지 비동기 Job 매니저가 공존한다.

| 매니저 | 위치 | 역할 |
| --- | --- | --- |
| `job_manager` | `service/job_manager.py` | 단일 영상 2D 파이프라인 (frame → MediaPipe → analysis → LLM). `synthesis_job_manager`로 점진적 통합 중. |
| `synthesis_job_manager` | `service/synthesis_job_manager.py` | 2-카메라 streaming synthesis 파이프라인. `DualVideoSynthesisCoordinator`로 좌/우 영상 chunk 동기화. |

### Job State

`queued → extracting → analyzing → generating_feedback → completed`
(중간 단계 실패 시 → `failed`)

### Service 모듈 분포

`service/`는 영역별로 다음처럼 묶인다.

- **Job orchestration** — `job_manager.py`, `synthesis_job_manager.py`, `dual_video_synthesis_coordinator.py`
- **Frame & pose** — `video_reader.py`, `pose_inference.py`, `skeleton_mapper.py`, `landmark_observation.py`
- **3D synthesis** — `skeleton_3d_synthesizer.py`, `triangulation.py`, `camera_calibration.py`, `frame_alignment.py`, `skeleton_3d_evaluator.py`, `skeleton3d_to_rack_mapper.py`
- **Analysis** — `analysis_pipeline.py` + `analysis_*.py` (preprocess, body_profile, cop, features, reps, kpis, thresholds, events, issues, visualization)
- **LLM** — `llm_feedback.py`, `llm_prompt_payload.py`
- **Repositories** — `rack_motion_repository.py`, `skeleton_artifact_repository.py`
- **Observability** — `benchmarking.py`

각 파일의 세부 역할은 루트 README의 "백엔드 아키텍처 / Service — 핵심 모듈" 표를 본다.

### Adapter

외부 라이브러리를 직접 만지는 유일한 경계.

| 파일 | 격리 대상 |
| --- | --- |
| `adapter/mediapipe_adapter.py` | MediaPipe Vision API (PoseLandmarker 초기화·추론·정리) |
| `adapter/opencv_adapter.py` | OpenCV `cv2.VideoCapture` 등 영상 I/O |

> Service는 외부 라이브러리를 직접 부르지 않고 항상 Adapter를 경유한다.

---

## 데이터 계약

분석 결과는 다음 3분할 구조로 응답된다(`schema/result.py`가 source of truth).

```jsonc
{
  "skeleton":    { /* 비디오 오버레이 UI용 프레임별 랜드마크 */ },
  "analysis":    { /* 대시보드 차트용 KPI, repSegments, issues 등 */ },
  "llmFeedback": { /* 코칭 텍스트: overallComment, highlights, corrections, coachCue */ }
}
```

프론트엔드와 분석 담당자는 이 3분할을 공통 어휘로 쓴다. 새 분석 항목을 넣을 때는 먼저 어느 블록 어느 필드에 들어갈지 정한 뒤 구현한다.

### Schema 파일

| 파일 | 역할 |
| --- | --- |
| `schema/job.py` | Job 생성·상태·에러 응답. |
| `schema/frame.py` | `FrameExtractionOptions`, `FrameChunk` 등. |
| `schema/pose.py` | `PoseChunk`, `PoseFrameResult`, `AlignedPoseChunkPair`. |
| `schema/synthesis.py` | streaming 합성 입력·출력. |
| `schema/result.py` | 3분할 최종 응답. **데이터 계약의 source of truth.** |
| `schema/rack_motion.py` | Stage1 랙 모션 뷰어 fixture. |
| `schema/benchmark.py` | 벤치마크 응답. |

---

## 부속 디렉터리

6-Layer 외에 백엔드 디렉터리에는 다음 보조 자산이 있다.

| 경로 | 역할 |
| --- | --- |
| `config/` | 포트, 경로 등 런타임 설정. |
| `fixtures/rack_motion/` | 랙 모션 뷰어 fixture JSON (`virtual_power_rack_dev_alignment.json` 등). |
| `scripts/run_3d_synthesis.py` | 2-view 영상에서 3D synthesis를 단발성으로 돌릴 때 쓰는 CLI 진입점. |
| `src/preset_estimations/` | preset pose JSON(추론 단계를 스킵하는 입력 자산). [`README`](./src/preset_estimations/README.md). |
| `tests/` | pytest 테스트(`test_analysis_pipeline.py`, `test_skeleton_3d_synthesizer.py`, `test_triangulation.py` 등). |
| `docs/` | 백엔드 자체 architecture / optimization / reference / examples 문서. |

---

## 폴더 읽는 순서

처음 백엔드를 만지는 팀원에게 권장하는 순서.

1. 이 `README.md`
2. `main.py` — 서버 진입점
3. `app.py` — 라우터 조립
4. `controller/synthesis.py` — 현재 권장 entry path
5. `service/synthesis_job_manager.py` — 합성 job 흐름
6. 본인이 맡은 도메인의 `service/...` 파일
7. `schema/result.py` — 데이터 계약

레이어 한 줄 요약:

- `controller/` — 입구
- `service/` — 실제 작업
- `schema/` — 주고받는 데이터 형식
- `adapter/` — 외부 라이브러리 연결부

---

## 데이터 분석 담당자 안내

분석 담당자가 우선 봐야 하는 파일은 다음 3개다.

- `service/analysis_pipeline.py` — 분석 흐름 오케스트레이션. 새 분석 로직의 기본 진입점.
- `schema/result.py` — 분석 결과가 들어갈 데이터 계약.
- 필요시 `service/skeleton_mapper.py` — 분석 입력으로 들어오는 skeleton 구조 확인.

원칙은 **결과 형식부터 합의하고, 그다음 분석 로직을 넣는다.** 즉:

1. 어떤 KPI·이슈를 추가할지 정의한다.
2. `schema/result.py`의 `analysis` 블록에 들어갈 필드를 먼저 정한다.
3. 그 후 `service/analysis_*.py`에 계산 로직을 추가한다.

분석 코드가 커지면 이미 영역별로 쪼개져 있으므로(`analysis_features.py`, `analysis_reps.py`, `analysis_kpis.py`, `analysis_issues.py`, …) 새 로직은 해당 영역 파일에 추가하고, 흐름은 `analysis_pipeline.py`에서 조립한다.

`controller/`, `adapter/`, `main.py`, `app.py`의 세부 구현은 분석 작업에 직접 필요하지 않다.

추가 가이드: [`docs/architecture/data-analysis-pipeline-guide.md`](./docs/architecture/data-analysis-pipeline-guide.md), [`docs/architecture/analysis-pipeline-design.md`](./docs/architecture/analysis-pipeline-design.md).

---

## 관련 문서

- [`../README.md`](../README.md) — 저장소 전체 개요, 6단계 로드맵, 프론트엔드 아키텍처, 두 저장소 운영 차이.
- [`../docs/onboarding.md`](../docs/onboarding.md) — 신규 팀원 로컬 셋업.
- [`../AGENTS.md`](../AGENTS.md) — 에이전트/협업 진입점.
- [`docs/architecture/`](./docs/architecture/) — 백엔드 architecture / API 통합 / LLM 통합 / 분석 파이프라인 설계 문서.
- [`docs/optimization/`](./docs/optimization/) — 벤치마크 / 최적화 기록.
- [`docs/reference/`](./docs/reference/) — MediaPipe PoseLandmarker 등 외부 참고 자료.
- [`docs/testing.md`](./docs/testing.md) — 테스트 가이드.
- [`src/preset_estimations/README.md`](./src/preset_estimations/README.md) — preset estimation JSON 입력 자산 안내.
