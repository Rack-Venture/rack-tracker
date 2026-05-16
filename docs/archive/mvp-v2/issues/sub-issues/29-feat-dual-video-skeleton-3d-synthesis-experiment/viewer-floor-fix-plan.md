# [fix] ThreeJS Skeleton Viewer 수직 축 / 지면 계산 구조 수정 계획
Parent: #29

## 문서 관계
- 이 문서는 `3d-skeleton-rendering-plan.md` (PLAN-04) 및 `3d-synthesis-redesign-review-plan.md` (PLAN-07)에서 파생한 세부 수정 계획이다.
- PLAN-07에서 조사한 "기울어 보임" 현상의 원인이 `ThreeJSSkeleton.jsx`의 `computeMetricViewFrame` 함수의 구조적 설계 오류로 특정되었고, 이 문서는 해당 수정의 범위, 결정, 구현 계획을 담는다.
- 커밋 단위 작업 이력과 승인 후 management log는 부모 관리 문서(`29-feat-dual-video-skeleton-3d-synthesis-experiment.md`)에 기록한다.
- 이 문서에는 버그 진단 근거, 수정 결정 사항, 구현 항목, 다음 액션만 담는다.

## Matrix Sync Rule
- 이 문서의 구현 항목 상태가 바뀌면 부모 관리 문서의 PLAN-08 row를 함께 갱신한다.
- 이 수정이 PLAN-04(3D 렌더링)의 외부 계약이나 viewer API를 바꾸면 PLAN-04 matrix의 해당 항목도 갱신한다.
- 부모 matrix에서 PLAN-08의 scope, priority, dependency가 바뀌면 이 문서의 matrix도 갱신한다.

---

## 문제 인식

### 증상
Three.js 뷰어에서 발 관절 삼각측량이 실패하는 구간(영상 초반부 포함)에 스켈레톤이 전면으로 약 38~40° 기울어진 채로 렌더링된다. 발 관절이 성공하는 프레임에서는 기울기가 2~5°에 불과해 사실상 수직이다.

### 진단 수치 (synth_f875a5e7.json)

| 프레임 | 발 성공 | ground 기준 관절 | tilt |
| --- | --- | --- | --- |
| 0 | ✗ | left_ear (얼굴) | **38°** |
| 10 | ✗ | 귀/상체 | 12° |
| 50 | ✗ | 눈 | 12° |
| 285 | ✓ | 실제 발 관절 | 3° |
| 500 | ✓ | 실제 발 관절 | 2° |
| 1000 | ✓ | 실제 발 관절 | 2° |

| 분류 | 프레임 수 | 비율 |
| --- | --- | --- |
| 발 성공 → tilt 2~5° (정상) | 3,156 | 87.7% |
| 발 실패, 성공 관절 있음 → tilt 10~38° | 381 | 10.6% |
| 전 관절 실패 → 렌더 없음 | 62 | 1.7% |

합성 JSON 좌표 자체는 정상이다. `panoptic_world_cm` 기준 Y축이 키 방향(더 음수 = 더 위), GT와 평균 ~3 cm 오차 수준으로 일치한다.

---

## 근본 원인: 수직 축을 스켈레톤에서 추정하는 구조적 오류

### 현재 코드가 하는 일

`computeMetricViewFrame`은 매 프레임마다 가시 관절의 Y 좌표 분포에서 수직 방향과 지면 위치를 추정한다.

```
groundY = max(발 관절 Y)  // 발 없으면 max(전체 성공 관절 Y)
bodyHeight = groundY - min(Y)
→ 이 두 값으로 scale, floorY를 결정해 Three.js 수직 축을 설정
```

발이 없으면 귀·눈이 `groundY` 기준이 된다. 얼굴 관절의 eye→ear 벡터가 panoptic world에서 이미 Y-Z 평면 기준 ~38° 기울어져 있으므로, 이를 수직 기준으로 삼으면 렌더 전체가 ~38° 기운다.

### 왜 이 접근 자체가 틀렸는가

수직 축과 지면 위치는 **좌표계가 정의하는 고정 속성**이다. 파워랙과 카메라 캘리브레이션이 이루어진 절대 가상 공간에서, "어느 축이 수직인가"와 "지면 Y값이 얼마인가"는 측정 환경이 결정한다. 이 값은 어떤 관절이 삼각측량에 성공했는지와 무관하다.

`panoptic_world_cm`의 경우:
- 수직 축: Y축, 더 음수 = 더 위 (캘리브레이션이 정의)
- 지면 Y: ≈ 0 cm (실측 확인: 발 성공 프레임의 발목 Y 평균 ≈ 0)

현재 코드는 이 고정 사실을 매 프레임 관절에서 재추정하고 있다. 관절 가시성은 오직 **표시 프레이밍**(centering, scale)에만 관여해야 한다.

### 두 역할의 혼용

| 역할 | 올바른 소스 | 현재 소스 |
| --- | --- | --- |
| 수직 축 방향 (up axis) | 좌표계 메타데이터 (synthesisInfo) | 가시 관절 Y 범위 ← **틀림** |
| 지면 위치 (ground plane Y) | 좌표계 메타데이터 (synthesisInfo) | 가시 관절 max Y ← **틀림** |
| 표시 중심 (centerX, centerZ) | 가시 관절 bounds | 가시 관절 bounds ✓ |
| 표시 scale | 가시 관절 bounds | 가시 관절 bounds ✓ |

---

## 결정된 수정 방향

### 핵심 원칙
수직 축과 지면은 좌표계 메타데이터에서 가져온다. 관절에서 추정하지 않는다.

### 구체적 변경

**① synthesisInfo에 좌표계 view 힌트 추가 (백엔드)**

`skeleton3d.v1`의 `synthesisInfo`에 viewer가 수직 축과 지면을 결정하는 데 필요한 필드를 추가한다.

```json
"synthesisInfo": {
  "coordinateSystem": "panoptic_world_cm",
  "viewHint": {
    "upAxis": "y",
    "upAxisDirection": "negative",
    "groundPlaneValue": 0.0
  }
}
```

- `upAxis`: 수직 방향을 나타내는 world 좌표 축 이름 (`"y"`, `"z"` 등)
- `upAxisDirection`: 해당 축에서 위쪽이 양수 방향인지 음수 방향인지 (`"positive"` / `"negative"`)
- `groundPlaneValue`: 해당 축 기준 지면 값 (panoptic_world_cm 기준 `0.0`)

`panoptic_world_cm`에서는 이 값이 고정이므로 하드코딩해도 무방하나, 나중에 `rack_session_world.v1`로 전환할 때 동일 구조로 확장된다.

**② computeMetricViewFrame 역할 분리 (프론트엔드)**

`computeMetricViewFrame`에서 수직 축/지면 계산을 제거하고, 두 역할을 명확히 분리한다.

```
[수직 축 / 지면]  ← synthesisInfo.viewHint (고정 메타데이터)
[표시 프레이밍]   ← 가시 관절 bounds (centering, scale)
```

수정 후 `toLandmarkVec3`의 Y 매핑:
```javascript
// upAxisDirection = "negative" → 더 음수 = 위 → groundPlaneValue - world_Y
y_render = (groundPlaneValue - world_Y) * scale + floorY
```

`groundPlaneValue`는 synthesisInfo에서 읽어온 상수이며, 관절에서 추정하지 않는다.

---

## Implementation Status & Decision Matrix

| ID | 구분 | 파일 | 상태 | 결정된 방향 | 다음 액션 |
| --- | --- | --- | --- | --- | --- |
| FIX-01 | synthesisInfo에 viewHint 추가 | `backend/service/skeleton_3d_synthesizer.py` | 구현 완료 | `synthesisInfo`에 `viewHint.upAxis`, `upAxisDirection`, `groundPlaneValue` 추가. `panoptic_world_cm` 기준 `upAxis="y"`, `upAxisDirection="negative"`, `groundPlaneValue=0.0`으로 고정 | #29 종료. schema 변경은 후속 이슈에서 재검토 |
| FIX-02 | adapter에서 viewHint 수신 | `frontend/src/features/analysis-session/adapters.js` | 구현 완료 | `adaptSkeleton3DPage`에서 `synthesisInfo.viewHint`를 읽어 3D frame에 보존 | #29 종료 |
| FIX-03 | computeMetricViewFrame 역할 분리 | `frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx` | 구현 완료 | 수직 축·지면 계산을 관절 추정에서 viewHint 상수로 교체. 관절 bounds는 centering(X, Z)과 scale 결정에만 사용 | #29 종료. 브라우저 visual regression은 후속 검증 |
| FIX-04 | HUD 렌더 소스 표시 | `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx` | 구현 완료 | 현재 프레임이 3D frame인지, 2D fallback인지, loading 중인지 HUD에 표시 | #29 종료 |
| FIX-05 | 전 관절 실패 프레임 처리 | `ThreeJSSkeleton.jsx` | 보류 | 성공 관절 0개 프레임은 기존 `hideAll` 경로를 유지한다. viewHint 도입 후 시각 검증은 별도 browser-level 테스트가 필요하다. | 후속 visual regression 이슈에서 검증 |

---

## 구현 범위

### 수정 대상 파일

| 파일 | 수정 내용 |
| --- | --- |
| `backend/service/skeleton_3d_synthesizer.py` | `synthesisInfo`에 `viewHint` 블록 추가 |
| `frontend/src/features/analysis-session/adapters.js` | `adaptSkeleton3DPage`에서 `viewHint` 수신 및 보존 |
| `frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx` | `computeMetricViewFrame`에서 수직 축·지면 추정 제거, viewHint 상수 사용 |
| `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx` | HUD 렌더 소스 표시 |

### 수정 불필요 (정상 동작 확인)

| 파일 | 이유 |
| --- | --- |
| `backend/service/triangulation.py` | 3D 좌표 자체 정상. Y축 방향, 값 범위, GT 대비 오차 모두 정상 |
| `backend/service/skeleton_3d_synthesizer.py` (삼각측량 로직) | 실패 관절 `success=false`, `position=null` 처리 정상 |
| `frontend/src/features/analysis-session/adapters.js` (기존 로직) | `renderable=false`, 좌표 0 기본값 처리 정상 |

---

## 검증 기준

1. Frame 0 (얼굴만 성공): ~38° 전면 기울기가 사라지고, 지면이 viewHint 기준 Y=0에 고정된다.
2. Frame 285 (발 성공): 기존과 동일하게 코가 위, 발이 아래(tilt ≤ 5°)로 표시된다.
3. 발 실패 381개 프레임에서 tilt가 viewHint 도입 후 발 성공 프레임 수준(≤ 5°)으로 감소한다.
4. 프레임 간 지면 위치가 흔들리지 않는다(관절 가시성이 바뀌어도 지면은 Y=0으로 고정).
5. HUD가 현재 프레임의 실제 렌더 소스(3D / 2D fallback / loading)를 표시한다.

---

## rack_session_world.v1 확장성

`viewHint` 구조는 나중에 product 좌표계로 전환할 때 동일하게 확장된다.

```json
"viewHint": {
  "upAxis": "z",
  "upAxisDirection": "positive",
  "groundPlaneValue": 0.0
}
```

`rack_session_world.v1`에서 Z-up을 쓰는 경우 위처럼 선언만 바꾸면 viewer 코드 변경 없이 동작한다.

---

## 보류
- temporal smoothing (발 성공 이전 프레임 관절을 인접 프레임으로 보간)
- 발 실패 구간 ghost 표시 (투명도를 낮춰 예상 위치를 hint로 표시)

## 다음 액션
- #29에서는 FIX-01~FIX-04 구현까지 완료하고 종료한다.
- 발 실패 프레임의 browser-level visual regression, tilt 수치 재측정, temporal smoothing 여부는 후속 검증 이슈에서 다룬다.
