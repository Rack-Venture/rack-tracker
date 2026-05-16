# 열린 질문

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/06_open_questions_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/06-open-questions.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
이 질문들은 rack-tracker가 독립적인 제품, 라이선스, 엔지니어링 결정을 내릴 때까지 미해결 상태로 남겨야 한다. 원본 프로젝트 구현 세부사항을 추론해서 채우지 않는다.

## #37 채택 검토 동기화 메모

이 문서는 #32 원본 열린 질문 목록을 보존한다. 2026-05-07에 일부 질문은 #37 채택 검토 문서에서 MVP v2 방향으로 재분류되거나 결정되었다. 현재 적용되는 채택 결정은 `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/06-open-questions.md`의 `2026-05-07 사용자 채택 결정` 절을 확인한다. 원본 질문 자체는 장기 제품/법무/엔지니어링 판단이 필요한 항목을 추적하기 위해 여기 남겨둔다.

## 라이선스 및 의존성 질문

- rack-tracker의 목표 라이선스는 무엇인가?
- rack-tracker는 배포될 것인가, 비공개로 유지될 것인가, 상업적으로 판매될 것인가, 아니면 network service로 제공될 것인가?
- 라이선스 audit 이후 어떤 third-party library를 허용할 수 있는가?
- calibration, tracking, numerical, video I/O dependency가 목표 라이선스와 호환되는가?
- 외부 example, model weight, dataset을 사용할 것인가? 사용한다면 어떤 라이선스인가?

## 데이터 및 테스트 Asset 질문

- 테스트에는 어떤 video data를 사용할 것인가: synthetic, 직접 capture, 또는 별도 라이선스가 있는 public data?
- 테스트에 쓰는 calibration capture와 rack measurement의 소유자는 누구인가?
- lifter video 또는 pose data에 privacy requirement가 있는가?
- 원본 프로젝트의 generated artifact를 사용하지 않고 어떤 sample output을 공개할 수 있는가?

## 카메라 및 동기화 질문

- 첫 milestone은 single-camera only인가, multi-camera only인가, 아니면 둘 다인가?
- 카메라에서 timestamp를 사용할 수 있는가, 아니면 frame number만 있는가?
- rolling shutter, dropped frame, variable frame rate, camera clock drift는 어떻게 처리해야 하는가?
- strict equal frame count가 processing을 block해야 하는가, 아니면 timestamp-based partial sync를 허용해야 하는가?
- 한 카메라에 frame이 누락되었을 때 사용자에게 어떤 동작을 보여줄 것인가?

## 캘리브레이션 질문

- rack-tracker가 처음 지원할 calibration target은 무엇인가?
- canonical unit은 meter, millimeter, calibration-target unit 중 무엇이어야 하는가?
- camera distortion은 preprocessing 중, projection/reconstruction 중, 또는 둘 다에서 correction할 것인가?
- rack anchor는 calibration capture에서 derive할 것인가, lifting video에서 detect할 것인가, manual entry로 받을 것인가, imported할 것인가?
- 비전문가 사용자를 위해 calibration quality를 어떻게 요약해야 하는가?

## 좌표 공간 질문

- 각 rack setup에서 표준 `RackWorldSpace` origin은 정확히 무엇이어야 하는가?
- mapping 이후 `x`는 lifter-left to lifter-right여야 하는가, camera-left to camera-right여야 하는가?
- 신뢰할 수 있는 ground plane이 없을 때 vertical axis는 어떻게 설정하는가?
- `RackWorldSpace`는 lift type별로 달라질 수 있는가, 아니면 session-global이어야 하는가?
- calibration과 manual rack measurement 전반의 unit conversion은 어떻게 검증해야 하는가?

## Target Schema 질문

- 실제 gym lighting에서 어떤 barbell endpoint를 안정적으로 detect할 수 있는가?
- squat, bench, deadlift, overhead press, rack-only check에 필요한 person keypoint는 무엇인가?
- rack feature는 static measurement여야 하는가, per-frame detection이어야 하는가, 아니면 둘 다인가?
- camera viewpoint가 bar를 가로지르거나 occlude할 때 left/right endpoint identity를 어떻게 유지해야 하는가?
- multi-person support가 필요한가, 아니면 첫 버전은 single lifter를 요구해야 하는가?

## Reconstruction 및 Quality 질문

- metric별 최소 허용 camera count는 무엇인가?
- reconstruction quality가 낮을 때 어떤 metric은 block하고 어떤 metric은 warning 처리해야 하는가?
- 어떤 reprojection error unit과 summary statistic을 보여줘야 하는가?
- camera contribution weight는 public schema의 일부여야 하는가, 아니면 diagnostic에만 있어야 하는가?
- single-camera estimate가 calibrated 3D로 오해되지 않도록 어떻게 label해야 하는가?

## Temporal Processing 질문

- bar endpoint에 허용 가능한 최대 interpolation span은 얼마인가?
- person keypoint에 허용 가능한 최대 interpolation span은 얼마인가?
- 어떤 metric은 smoothed trajectory를 사용할 수 있고, 어떤 metric은 raw reconstructed position이 필요한가?
- exported report에서 processed value를 raw measurement에 어떻게 연결해야 하는가?
- velocity와 acceleration은 영구 저장해야 하는가, 아니면 필요할 때 계산해야 하는가?

## Rack Event Policy 질문

- J-cup 또는 safety pin에 "near"하다는 것은 어떤 distance로 정의하는가?
- contact event를 candidate event가 아닌 것으로 부르려면 어떤 evidence가 필요한가?
- event flicker를 피하려면 temporal hysteresis가 얼마나 필요한가?
- event detection은 bar center, 양쪽 endpoint, 또는 endpoint-specific proximity 중 무엇에 의존해야 하는가?
- event confidence는 rack anchor quality, bar endpoint quality, temporal continuity를 어떻게 결합해야 하는가?

## Output 및 Product 질문

- 첫 milestone에 필요한 output format은 무엇인가?
- diagnostic은 user-visible, developer-only 또는 둘 다여야 하는가?
- 실제 session이 생긴 뒤 어떤 schema migration policy가 필요한가?
- 모든 exported file이 가져야 하는 최소 metadata는 무엇인가?
- 어떤 UI 또는 reporting feature가 vision core 범위 밖이며 별도로 만들어져야 하는가?
