# [design] 3D 합성 API 및 분석 파이프라인 리팩토링 계획
Parent: #29

## 문서 관계
- 이 문서는 `3d-skeleton-synthesizer-plan.md`의 하위 API/분석 계획이다.
- 목적은 3D 합성 결과를 기존 분석 파이프라인에 바로 섞지 않고, 별도 API와 adapter 경계를 통해 점진적으로 연결하는 방식을 정의하는 것이다.
- 이 문서는 코드 변경 없이 계약과 리팩토링 순서만 정리한다.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## Implementation Status & Decision Matrix

| ID | 구분 | 레이어/단계 | 상태 | 결정된 방향 | 결정 필요 사항 | 다음 액션 | 참조 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-01 | synthesis job 생성 | API contract | 구현 완료 | `POST /synthesis/jobs`는 pair manifest 기반 request를 받는다. manifest 안에 A/B source job, camera binding, calibration, sync, landmark/output 좌표계를 묶는다. | 없음 | request schema 변경 시 frontend client와 함께 갱신한다. | Pair manifest 계약 |
| API-02 | synthesis 상태 모델 | job orchestration | 구현 완료 | 기존 `JobStatusResponse` envelope(`jobId`, `status`, `progress`, `error`)를 재사용한다. top-level `status`는 기존처럼 `queued`, 현재 stage, `completed`, `failed` 중 하나로 두고 synthesis 세부 정보는 `progress.stageDetails.synthesis`에 둔다. | 없음 | stage 이름이나 detail 필드가 바뀌면 frontend polling 표시도 함께 갱신한다. | Synthesis 상태 모델 계약 |
| API-03 | skeleton3d 조회 | result API | 구현 완료 | 3D skeleton summary와 frame page 조회를 분리한다. | pagination 정책은 현재 offset/limit 기반으로 구현돼 있으며 추가 cursor 전환은 필요 시 검토한다. | 긴 결과에서 page size와 prefetch 정책만 추가 검증한다. | 후보 엔드포인트 |
| API-04 | evaluation 조회 | result API | 구현 완료 | GT 또는 reprojection 기반 평가 결과를 별도 endpoint로 둔다. | evaluation artifact가 optional일 때 404 응답을 유지할지 별도 summary를 줄지 결정 여지가 있다. | optional evaluation 응답 규칙만 문서로 보강한다. | 후보 엔드포인트 |
| API-05 | 분석 adapter | analysis boundary | 보류 | `Skeleton3DAnalysisAdapter`가 3D feature namespace와 mask를 만드는 작업은 아직 구현하지 않고 후속 범위로 둔다. | 없음 | synthesis/viewer 검증 뒤 별도 work item으로 분리한다. | Adapter 책임 |
| API-06 | 기존 분석 파이프라인 확장 | analysis pipeline | 보류 | `analysis_pipeline.py`의 전면 3D-aware 확장은 adapter 안정화 뒤로 미룬다. | 없음 | adapter 검증 후 별도 refactor work item으로 분리한다. | 분석 파이프라인 연결 순서 |
| API-07 | 실시간 synthesis SSE | future scope | 보류 | 첫 버전은 batch synthesis와 조회 API를 우선한다. | 없음 | batch API 검증 뒤 streaming 필요성을 재평가한다. | 보류 |

## 현재 상태
- `backend/service/analysis_pipeline.py`는 단일 2D 스켈레톤 dict 를 입력으로 받는다.
- `backend/service/analysis_preprocess.py`는 `frames[].landmarks[]`의 `x`, `y` 화면 좌표 중심 처리를 전제로 한다.
- `backend/controller/synthesis.py`와 `backend/service/synthesis_job_manager.py`가 별도 synthesis job 생성, 상태 조회, result, `skeleton3d`, evaluation 조회 endpoint를 이미 제공한다.
- `frontend/src/api/analysisClient.js`와 `frontend/src/components/sections/Skeleton3DSynthesisSection/`는 synthesis job 생성 후 polling 기반으로 상태를 추적하고 paged `skeleton3d`를 로드한다.

## 목표 API
- pair manifest 로 저장된 두 2D skeleton 결과와 camera binding을 묶어 synthesis job 을 생성한다.
- synthesis job 은 기존 analysis job 과 분리된 endpoint 를 갖되, 상태 조회의 top-level envelope 는 기존 job status 와 호환되게 유지한다.
- 합성 결과는 별도 3D JSON으로 저장하고, 필요 시 analysis adapter 를 통해 후속 분석으로 넘긴다.

## Pair manifest 계약
- `POST /synthesis/jobs`의 입력 source of truth는 느슨한 job id 2개가 아니라 `pairManifest`다.
- pair manifest 는 Video A/B slot, source job id, camera id, calibration ref, sync 설정, landmark set, output coordinate system을 한 덩어리로 보존한다.
- 첫 구현은 inline `pairManifest`를 request body로 받는다. 나중에 DB나 object storage가 생기면 같은 shape를 저장한 `pairManifestRef`를 추가할 수 있다.
- A/B slot 순서는 job metadata와 `skeleton3d.v1.synthesisInfo`에 그대로 기록한다.

권장 request shape:

```json
{
  "pairManifest": {
    "schemaVersion": "synthesis_pair_manifest.v1",
    "sources": {
      "A": {
        "sourceJobId": "job_video_a",
        "cameraId": "00_00"
      },
      "B": {
        "sourceJobId": "job_video_b",
        "cameraId": "00_01"
      }
    },
    "calibrationRef": "171204_pose1/171204_pose1/calibration_171204_pose1.json",
    "sync": {
      "mode": "timestamp",
      "timestampDomain": "media_time_ms",
      "maxDeltaMs": 16.7,
      "fallback": "frameIndex_for_gt_aligned_dataset_only"
    },
    "landmarkSet": "mediapipe_pose_33",
    "outputCoordinateSystem": "panoptic_world_cm"
  },
  "options": {
    "runEvaluation": false
  }
}
```

검증 규칙:
- `sources.A.sourceJobId`와 `sources.B.sourceJobId`는 서로 달라야 한다.
- 두 source job 은 완료된 2D analysis job 이어야 하고 skeleton artifact 를 조회할 수 있어야 한다.
- `sources.A.cameraId`와 `sources.B.cameraId`는 서로 달라야 하며 `calibrationRef` 안에 존재해야 한다.
- `sync.mode`, `landmarkSet`, `outputCoordinateSystem`은 지원 목록에 없는 값을 거부한다.

## Synthesis 상태 모델 계약
- 공유 field: `jobId`, `status`, `progress`, `error`는 기존 2D `JobStatusResponse`와 같은 의미를 유지한다.
- 분리 field: 첫 구현의 synthesis 전용 정보는 `progress.stageDetails.synthesis` 안에 둔다.
- `status` 값은 기존 job status convention에 맞춰 `queued`, 현재 synthesis stage, `completed`, `failed` 중 하나를 사용한다. 별도 `running` enum은 두지 않는다.
- `progress.stage`는 synthesis 전용 stage 이름을 사용한다.
- `error`는 기존 `code`, `message` shape 를 재사용하되, code prefix 는 `synthesis_`로 둔다.

권장 synthesis stage:
- `validating_manifest`
- `loading_source_artifacts`
- `aligning_frames`
- `triangulating`
- `writing_artifacts`
- `evaluating`
- `completed`

권장 status response 추가 payload:

```json
{
  "jobId": "synth_123",
  "status": "triangulating",
  "progress": {
    "stage": "triangulating",
    "currentStep": 4,
    "totalSteps": 6,
    "ratio": 0.66,
    "stageDetails": {
      "synthesis": {
        "sourceJobIds": ["job_video_a", "job_video_b"],
        "cameraPair": ["00_00", "00_01"],
        "pairedFrameCount": 320,
        "artifactRefs": {}
      }
    }
  },
  "error": null
}
```

## 후보 엔드포인트
- `POST /synthesis/jobs`
  - 입력: inline `pairManifest`, options
  - 출력: synthesis job id, initial status
- `GET /synthesis/jobs/{job_id}`
  - 합성 상태, 진행률, 오류 정보
- `GET /synthesis/jobs/{job_id}/result`
  - 3D skeleton summary 및 quality summary
- `GET /synthesis/jobs/{job_id}/skeleton3d`
  - 3D frame page 조회
- `GET /synthesis/jobs/{job_id}/evaluation`
  - GT 또는 reprojection 기반 평가 결과

## 분석 파이프라인 연결 순서
1. 3D 합성 API는 기존 2D analysis API와 분리한다.
2. 3D JSON 스키마가 안정될 때까지 기존 `analysis_pipeline.py`는 수정하지 않는다.
3. 별도 adapter 를 만들어 3D JSON에서 분석에 필요한 feature shape 만 추출한다.
4. 3D 기반 분석이 필요한 지표를 기존 2D 지표와 분리해 설계한다.
5. 충분히 안정화된 뒤 `analysis_pipeline.py`를 2D/3D 입력을 구분하는 구조로 확장한다.

## Adapter 책임
- 3D 좌표계와 단위를 명시한다.
- 사용할 관절 subset 을 고른다.
- 실패한 관절/프레임을 분석 대상에서 제외하거나 mask 로 전달한다.
- 기존 2D feature 이름과 충돌하지 않게 3D feature namespace 를 분리한다.

## 보류
- 3D 합성 결과를 기존 `/jobs/{job_id}/result`에 직접 병합
- 기존 2D 분석 로직의 전면 재작성
- LLM feedback 의 3D 입력 전환
- 실시간 synthesis SSE 연결
