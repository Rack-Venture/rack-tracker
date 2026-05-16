# [design] Three.js 3D 스켈레톤 렌더링 계획
Parent: #29

## 문서 관계
- 이 문서는 `3d-skeleton-synthesizer-plan.md`의 하위 시각화 계획이다.
- 목적은 3D 합성 결과 JSON을 사람이 검증할 수 있도록 Three.js 기반 viewer 요구사항을 정리하는 것이다.
- 이 문서는 코드 변경 없이 렌더링 요구사항과 UI 범위만 정의한다.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## Implementation Status & Decision Matrix

| ID | 구분 | 레이어/단계 | 상태 | 결정된 방향 | 결정 필요 사항 | 다음 액션 | 참조 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RND-01 | viewer 입력 계약 | API/output schema | 구현 완료 | 현재 `frontend/src/components/sections/Skeleton3DSynthesisSection/`는 `skeleton3d.v1` page 응답을 adapter로 정규화해 canvas, timeline, mode panel, session/status panel 구조를 유지한다. | 없음 | API page response shape가 바뀌면 adapter와 section props를 함께 갱신한다. | 입력, 현 frontend 청사진 |
| RND-02 | 기본 skeleton 렌더링 | Three.js scene | 구현 완료 | 기본 topology는 MediaPipe33으로 고정하고 `POSE_EDGES` 기반 Three.js renderer를 사용한다. | COCO19 subset overlay는 아직 구현하지 않았다. | COCO19 overlay가 필요해질 때 별도 범위로 분리한다. | 기본 렌더링, skeleton topology 옵션 |
| RND-03 | 품질 표현 | visualization | 구현 완료 | `success=false`, reprojection error, source visibility를 시각적으로 구분한다. 현재 구현은 색상=reprojection error, opacity=visibility, ghost bone=`success=false` 조합을 사용한다. | timeline marker와 고급 quality legend는 아직 단순하다. | 실제 합성 artifact 기준으로 품질 표현 가독성을 검증한다. | 품질 표현, RND-03 결정 가이드 |
| RND-04 | 재생 제어 | UI controls | 구현 완료 | frame scrubber, play/pause, 현재 frame metadata를 제공하고, `skeleton3d`는 page/cache 방식으로 점진 로드한다. | 전체 preload와 hybrid 전환 정책은 아직 따로 두지 않는다. | 긴 clip 기준 cache/prefetch 체감만 추가 검증한다. | 기본 렌더링, RND-04 결정 가이드 |
| RND-05 | 반응형/검증 | frontend verification | 검증 필요 | desktop/mobile에서 canvas가 비어 있지 않고 bounds 기반 framing을 적용한다. | 없음 | Playwright screenshot과 canvas pixel check를 실행 기준으로 둔다. | 요구사항 |
| RND-06 | 편집/실시간 기능 | future scope | 보류 | 첫 버전은 검증 viewer이며 관절 보정 UI와 실시간 합성 stream 렌더링은 제외한다. | 없음 | 합성 결과 검증 viewer가 안정화된 뒤 별도 issue로 분리한다. | 보류 |

## 목표
- 합성된 3D 스켈레톤을 프레임 단위로 재생한다.
- 카메라 쌍, 프레임 정합 상태, 관절별 품질을 시각적으로 확인한다.
- triangulation 실패 관절과 reprojection error 가 큰 관절을 빠르게 찾을 수 있게 한다.

## 입력
- 3D 합성 결과 JSON
- 선택 입력: 원본 Video A/B metadata
- 선택 입력: GT 비교 결과 JSON

## 현 frontend 청사진
- 현재 `frontend/src/components/sections/Skeleton3DSynthesisSection/`에 Three.js 기반 검증 UI의 1차 청사진이 있다.
- `Skeleton3DSynthesisSection.jsx`는 canvas column, timeline, synthesis mode, camera preset, session status, joint visibility table 구조를 이미 가진다.
- `ThreeJSSkeleton.jsx`는 Three.js scene, OrbitControls, grid floor, axis helper, MediaPipe33 joint sphere, MediaPipe33 bone line 렌더링 path를 이미 가진다.
- 현재 구현은 `createSynthesisJob()`과 `getSynthesisSkeleton3DPage()`로 생성된 paged `skeleton3d.v1` 결과를 `adaptSkeleton3DPage()`로 정규화해 우선 사용한다.
- `synthesizeFrames()`의 A/B 평균 로직은 3D 결과가 아직 없거나 사용자가 `A only`, `B only` 모드를 선택했을 때의 fallback/debug 경로로만 남아 있다.
- 따라서 현재 viewer의 핵심 구조는 이미 `skeleton3d` 중심이고, 이후 변경 포인트는 화면 재설계보다 품질 표현과 검증 기준 보강에 가깝다.

## 기본 렌더링
- 좌표축 표시
- 바닥 또는 기준 평면 표시
- 기본 MediaPipe33 관절 연결선 표시
- 선택 옵션으로 COCO19 subset 연결선 표시
- 관절 점 표시
- 프레임 scrubber 와 play/pause 제어
- 현재 `frameIndex`, `timestampMs`, usable joint 비율 표시

### skeleton topology 옵션
- 기본값: `mediapipe33`
- 선택값: `coco19_subset`
- MediaPipe33은 합성기의 기본 landmark set과 일치하므로 기본 skeleton display로 사용한다.
- COCO19 subset은 GT 평가와 비교할 때 유용하지만, MediaPipe에 직접 없는 `neck`, `mid_hip` 같은 derived joint를 포함하면 구현 비용이 커진다.
- 첫 버전의 COCO19 옵션은 "MediaPipe33에서 직접 대응되는 관절만 선별해 보여주는 subset overlay"로 제한한다.
- derived joint 렌더링은 GT 평가에서 필요성이 확인되면 별도 항목으로 분리한다.

## 품질 표현
- `success=false` 관절은 흐리게 표시하거나 숨김 처리한다.
- reprojection error 가 큰 관절은 색상으로 구분한다.
- source visibility 가 낮은 관절은 별도 opacity 로 표시한다.
- 프레임 전체 품질이 낮으면 timeline 에 marker 를 남긴다.

## RND-03 결정 가이드: 품질 표현

품질 표현은 "정확한 디버깅"과 "한눈에 보기" 사이의 선택이다. 첫 구현에서는 합성 결과가 맞는지 빠르게 검증하는 것이 목적이므로, 너무 많은 신호를 한 화면에 겹치지 않는 쪽이 안전하다.

### 결정 1. reprojection error 색상 기준
- 추천안: 합성기 threshold를 그대로 쓴다.
- 예시: `maxReprojectionErrorPx=8.0`이면 `0~4px=정상`, `4~8px=주의`, `8px 초과=실패`로 표시한다.
- 장점: backend가 실패로 판단한 기준과 viewer 색상이 일치한다.
- 단점: 첫 실험 결과에서 8px가 너무 엄격하거나 느슨하면 색상이 한쪽으로 몰릴 수 있다.

대안:
- viewer 전용 color scale을 둔다.
- 장점: 시각화는 더 보기 좋게 조정할 수 있다.
- 단점: backend 성공/실패 기준과 viewer 색상이 어긋나 사용자가 다른 결론을 낼 수 있다.

### 결정 2. `success=false` 관절 표시 방식
- 추천안: 실패 관절은 완전히 숨기지 않고 ghost 상태로 표시한다.
- ghost 상태는 낮은 opacity, 회색 계열, 연결선 약화로 표현한다.
- 장점: 어떤 관절이 실패했는지 위치와 패턴을 바로 볼 수 있다.
- 단점: 실패 관절이 많으면 화면이 지저분해진다.

대안:
- 실패 관절을 숨긴다.
- 장점: 성공한 3D skeleton만 깨끗하게 보인다.
- 단점: 실패 위치를 찾는 디버깅 도구로는 약해진다.

### 결정 3. source visibility 반영 방식
- 추천안: visibility는 opacity에만 반영한다.
- 장점: 색상은 reprojection error에만 쓰이므로 의미가 겹치지 않는다.
- 단점: opacity 차이가 작은 화면이나 밝은 배경에서는 덜 보일 수 있다.

대안:
- visibility가 낮은 관절에 별도 outline 또는 marker를 붙인다.
- 장점: 낮은 visibility 관절이 더 잘 보인다.
- 단점: reprojection error marker와 겹쳐 UI가 복잡해진다.

### 결정 4. timeline marker 기준
- 추천안: frame의 `usableJointRatio`가 0.7 미만이거나 `meanReprojectionErrorPx`가 합성기 threshold를 넘으면 marker를 찍는다.
- 장점: 스크러버에서 문제가 큰 frame을 빠르게 찾을 수 있다.
- 단점: 좋은 frame과 나쁜 frame의 경계가 데이터셋마다 달라질 수 있다.

대안:
- 실패 관절 수가 특정 개수 이상일 때만 marker를 찍는다.
- 장점: 기준이 단순하다.
- 단점: 중요한 관절 하나가 크게 실패한 frame을 놓칠 수 있다.

## UI 위치
- 첫 버전은 기존 분석 UI에 억지로 결합하지 않는다.
- 합성 결과 검증용 별도 viewer 섹션 또는 개발용 route 로 둔다.
- 이후 안정화되면 `CoreDemoSection` 결과 영역과 연결한다.

## RND-04 결정 가이드: 재생과 로딩 정책

긴 합성 결과를 viewer가 어떻게 읽을지는 성능과 구현 난이도를 동시에 결정한다. 현재 프론트 청사진은 `skeletonPage.frames`를 한 번에 가진다는 가정이 있지만, 실제 `skeleton3d.v1` 결과는 길어질 수 있으므로 page/cache 정책을 정해야 한다.

### 옵션 A. 전체 JSON preload
- 방식: `skeleton3d.v1` 전체 frames 배열을 한 번에 내려받고 프론트 메모리에 올린다.
- 장점: 구현이 가장 쉽고 scrub/playback이 단순하다.
- 단점: 긴 영상에서 초기 로딩이 길고 브라우저 메모리 사용량이 커진다.
- 적합한 경우: 작은 fixture, 개발용 smoke test, 짧은 clip.
- 부적합한 경우: 실제 업로드 영상, 수천 frame 이상 결과.

### 옵션 B. page 기반 로딩
- 방식: `startFrame`/`limit` 또는 cursor로 필요한 frame page만 요청한다.
- 장점: 긴 영상에서도 초기 로딩과 메모리를 안정적으로 제어할 수 있다.
- 단점: scrub을 크게 이동할 때 loading state, prefetch, cache miss 처리가 필요하다.
- 적합한 경우: 실제 MVP viewer, 긴 영상 검증.
- 구현 포인트: 현재 frame 주변 page를 미리 가져오고, playback이 cache 끝에 닿기 전에 다음 page를 prefetch한다.

### 옵션 C. hybrid
- 방식: 짧은 결과는 전체 preload, 긴 결과는 page 기반으로 자동 전환한다.
- 추천안: 첫 제품 구현은 이 방식이 가장 현실적이다.
- 예시 기준: `totalFrames <= 600`이면 preload, 그 이상이면 page mode.
- 장점: fixture 개발 속도와 실제 영상 안정성을 둘 다 얻는다.
- 단점: viewer adapter가 두 경로를 모두 처리해야 한다.

### page response에 필요한 최소 필드
```json
{
  "schemaVersion": "skeleton3d.v1",
  "page": {
    "startFrame": 0,
    "limit": 120,
    "totalFrames": 3481,
    "nextStartFrame": 120
  },
  "timeline": {
    "durationMs": 116149.0,
    "fps": 29.97
  },
  "synthesisInfo": {
    "landmarkSet": "mediapipe_pose_33",
    "thresholds": {
      "maxReprojectionErrorPx": 8.0
    }
  },
  "qualitySummary": {
    "usableJointRatio": 0.82,
    "meanReprojectionErrorPx": 2.4
  },
  "frames": []
}
```

### scrub/playback 동작 결정
- 추천안: scrub 이동 시 해당 frame의 page가 없으면 canvas에 마지막 frame을 유지하고 loading overlay를 짧게 표시한다.
- 추천안: playback 중 다음 page가 아직 없으면 재생을 잠시 멈추지 않고, cache에 있는 마지막 frame까지 진행한 뒤 다음 page가 도착하면 이어간다.
- 대안: page가 없으면 즉시 pause한다.
- pause 방식은 구현이 단순하지만, 네트워크나 디스크 지연이 작은 경우에도 재생이 자주 끊겨 보일 수 있다.

## 요구사항
- 데스크톱과 모바일에서 canvas 가 비어 있지 않아야 한다.
- 모델 중심이 화면 밖으로 나가지 않도록 bounds 기반 카메라 framing 을 적용한다.
- 긴 영상은 전체 JSON을 한 번에 렌더링하지 않고 프레임 단위 접근이 가능해야 한다.
- 렌더링은 합성 정확도 검증을 위한 도구이며, 초기 MVP에서 편집 기능은 제외한다.

## 보류
- 실시간 합성 스트림 렌더링
- 관절 수동 보정 UI
- 3개 이상 카메라 frustum 동시 렌더링
- 분석 피드백과 시각화의 완전 통합
