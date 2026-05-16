# Rack-Tracker 파이프라인 계약

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/01_pipeline_contract_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/01-rack-tracker-pipeline-contract.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
이 문서는 rack-tracker 비전 코어를 위한 정제된 clean-room 계약이다. 기능 경계, 산출물 계약, 좌표계 의무, 실패 범주만 기록한다. 조사 대상 프로젝트의 소스 코드, 소스 명명, 내부 제어 흐름, 테스트, 샘플 데이터, 생성 산출물 재사용을 허가하지 않는다.

## 범위 경계

- 범위 포함: 카메라 입력, 프레임 인덱싱과 동기화, 이미지 전처리, 2D 타깃 관측, 캘리브레이션, 다중 뷰 3D 재구성, 엔티티 조립, 시간축 후처리, 랙 분석, 진단.
- 범위 제외: GUI 상태, 노트북 생성, 외부 3D 애플리케이션 내보내기, 시각 주석 UI, 번들 샘플 데이터, 원본 프로젝트 폴더 관례.
- 라이선스 경계: 조사 대상 프로젝트의 라이선스 조건을 이 저장소로 전이하지 않는다. 별도의 법적 승인이 없는 한 rack-tracker는 직접 코드 재사용, 테스트 문구 복사, 메시지 복사, 파일 레이아웃 복사, 생성 산출물 복사를 금지된 것으로 취급해야 한다.

## 단계 계약

| 단계 | 책임 | 입력 | 출력 | 실패 조건 | 재시작 산출물 |
| --- | --- | --- | --- | --- | --- |
| `SessionManifest` | 하나의 분석 실행을 설명하고 모든 입력을 안정적인 id에 바인딩한다. | 사용자가 선택한 카메라 소스, 처리 설정, 선택적 캘리브레이션 번들, 타깃 스키마. | 카메라 id, 타깃 id, 의도한 출력 공간, 산출물 위치를 포함한 버전 관리 manifest. | 사용 가능한 카메라 소스 없음, 중복 id, 지원하지 않는 미디어, 필수 설정 누락. | Manifest와 검증 보고서. |
| `CameraSource` | 원본 미디어를 수정하지 않고 프레임과 카메라 메타데이터를 노출한다. | 비디오 파일, 스트림, 캡처 장치 또는 미리 추출된 프레임. | `camera_id`, `frame_index`, 사용 가능한 경우 timestamp, 이미지 크기, FPS 추정치, 프레임 수를 포함한 카메라별 프레임 스트림. | 소스를 열 수 없음, 필요할 때 프레임 수를 알 수 없음, 지원하지 않는 코덱, 읽을 수 없는 프레임. | 카메라 인벤토리와 미디어 probe 보고서. |
| `FrameIndex` | 카메라 로컬 프레임을 공유 논리 시간으로 매핑한다. | 카메라 메타데이터, 프레임 수, timestamp, 선택적 offset. | 동기화 그룹, 프레임 가용성 테이블, 동기화 경고. | 빈 카메라 집합, 조정 불가능한 프레임 범위, 설정 정책을 초과하는 timestamp gap, strict sync가 필요할 때 프레임 수 불일치. | 프레임 인덱스 테이블과 동기화 진단. |
| `FramePreprocessor` | 되돌릴 수 있는 좌표 매핑을 보존하면서 detector-ready 이미지를 만든다. | 원본 이미지 프레임, 전처리 설정, 캘리브레이션 왜곡 정책. | 전처리된 프레임과 `ImageSpace`에서 `PreprocessedImageSpace`로, 그리고 역방향으로 가는 `PreprocessTransform`. | transform을 표현할 수 없음, 이미지가 유효하지 않게 됨, 필수 왜곡 메타데이터 누락, 출력 크기가 detector와 호환되지 않음. | 전처리 transform 테이블. 전처리 이미지는 선택적 cache 산출물. |
| `TargetDetector2D` | detector별 출력을 rack-tracker 관측으로 변환한다. | 전처리된 프레임, detector adapter, 타깃 스키마. | 원본 `ImageSpace`의 `Observation2D`, confidence, detector 메타데이터. | detector 사용 불가, 타깃 스키마 비호환, 출력을 원본 이미지 픽셀로 다시 매핑할 수 없음. | 원시 2D 관측 산출물과 detector 실행 보고서. |
| `ObservationStore2D` | 재구성과 디버깅을 위해 검증된 카메라별 관측을 보존한다. | `Observation2D`, 카메라 id, 프레임 인덱스, 전처리 transform. | 누락값, confidence, visibility 요약을 포함한 버전 관리 2D 관측 store. | shape 불일치, 타깃 id 누락, 잘못된 좌표 공간, 선언 범위를 벗어난 confidence. | 2D 관측 store와 검증 보고서. |
| `CalibrationBundle` | 카메라 intrinsics, distortion, extrinsics, 캘리브레이션 타깃, capture-world 정의를 설명한다. | rack-tracker 소유 JSON/TOML calibration 입력, 캘리브레이션 미디어 또는 external import adapter가 변환한 외부 제공 캘리브레이션 파일, 타깃 설명, 단위 선언. | `rack_motion.calibration_bundle.v1`, `CaptureWorldSpace`, `rack_motion.calibration_quality_report.v1`. | 필수 카메라 누락, 잘못된 캘리브레이션 단위, 사용할 수 없는 intrinsics/extrinsics, camera id mismatch, streaming session과 calibration source/version 불일치, 필요할 때 ground-plane 또는 anchor alignment 실패. | 캘리브레이션 번들 JSON artifact와 캘리브레이션 품질 보고서 JSON artifact. |
| `ReconstructionEngine3D` | 여러 카메라의 2D 관측을 3D 타깃 좌표로 합성한다. | `Observation2D`, `CalibrationBundle`, 프레임 인덱스, 재구성 설정. | `Reconstruction3D`, reprojection error, 사용된 카메라 수, 카메라별 visibility, 선택적 카메라 contribution weight. | 카메라 부족, 캘리브레이션 누락, 잘못된 좌표 채널, rack-tracker 정책상 높은 불확실성. | 원시 재구성 산출물과 재구성 품질 보고서. |
| `EntityFrame3D` | 타깃 포인트를 rack-tracker 엔티티로 바인딩한다. | `Reconstruction3D`, 타깃 스키마, world-space 정의. | 품질 요약을 포함한 프레임별 person, barbell, rack 엔티티. | 필수 엔티티 타깃 누락, 모호한 side label, 일관되지 않은 좌표 공간, 설정 정책상 불가능한 엔티티 geometry. | 엔티티 프레임 산출물. |
| `WorldSpaceMapper` | capture-world 좌표를 rack-centered 분석 좌표로 매핑한다. | Capture-world 3D 포인트, rack anchor 관측, transform 정책. | `RackWorldSpace` transform과 매핑된 엔티티 프레임. | rack anchor 누락, transform underdetermined, 단위 불일치, 정책 기준 이하의 alignment 품질. | World-space 정의와 alignment 보고서. |
| `TemporalPostProcessor` | 원시 데이터를 보존하면서 분석 준비가 된 trajectory를 만든다. | 원시 엔티티 프레임, 프레임 인덱스, 품질 metric, 시간축 설정. | 처리된 엔티티 프레임, interpolation span, smoothing/filter 메타데이터, velocity-ready trajectory. | gap이 fill 정책을 초과함, 시간축 연산에 필요한 프레임레이트 누락, 후처리 데이터를 원시 소스 프레임에 연결할 수 없음. | 처리된 엔티티 산출물과 시간축 진단. |
| `RackAnalyzer` | 매핑된 엔티티에서 rack-domain event와 lift metric을 계산한다. | `RackWorldSpace` 엔티티 프레임, rack/bar/person 스키마, event 정책. | bar path, endpoint asymmetry, rack proximity, support-contact event, rep segmentation 후보, 분석 품질 보고서. | rack anchor 누락, bar endpoint 누락, person identity 미해결, event 정책 미지정. | 분석 보고서와 metric 테이블. |

## 단일 카메라 경계

단일 카메라 출력은 캘리브레이션된 다중 뷰 3D와 동등하게 취급해서는 안 된다. rack-tracker는 preview와 coarse analysis를 위해 별도의 `ImagePlaneEstimate` 또는 `SingleCameraEstimate`를 지원할 수 있지만, 다른 reconstruction mode와 quality profile로 표시해야 한다.

## 산출물 경계

rack-tracker는 원시 산출물과 처리 산출물을 분리해야 한다.

- 원시 소스 메타데이터와 프레임 인덱스.
- 원본 이미지 픽셀의 원시 2D 관측.
- rack-tracker 소유 캘리브레이션 번들, 캘리브레이션 품질 보고서, 좌표 공간 정의. 사람이 관리하는 입력은 TOML 또는 JSON을 허용할 수 있지만, downstream 영구 산출물은 버전 관리된 JSON artifact여야 한다.
- `CaptureWorldSpace`의 원시 3D 재구성.
- `RackWorldSpace`의 매핑된 3D 엔티티.
- 원시 프레임 provenance를 포함한 후처리 trajectory.
- sync, detection, reconstruction, alignment, temporal edit에 대한 진단.
- 사용자 소비용 export. 진단과 분리해서 유지한다.

모든 영구 산출물은 `schema_version`, `session_id`, 좌표가 있을 때 `space_id`, 그리고 camera, frame, target, entity 정의로 다시 join할 수 있는 충분한 id를 포함해야 한다.
