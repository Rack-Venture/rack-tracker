# hdVideos_2min

CMU Panoptic Studio `171204_pose1` 시퀀스의 HD 영상 2개를 **시작 지점부터 2분 00초**까지 트리밍한 단축 클립 모음.

## 목적

#29 두 동영상 스켈레톤 추출 및 3D 합성 실험의 준비 작업.  
원본 영상(약 17분 36초)을 전부 처리하면 MediaPipe 실행 비용이 크므로, 초기 파이프라인 검증 단계에서 2분 클립을 사용한다.

## 파일 목록

| 파일명 | 카메라 ID | 크기 |
|--------|-----------|------|
| `hd_00_11_2min.mp4` | 00_11 | 213.6 MB |
| `hd_00_21_2min.mp4` | 00_21 | 304.4 MB |

총 합계: 약 518.0 MB (0.51 GB)

## 영상 사양

- 해상도: 1920 × 1080
- 프레임레이트: 29.97 fps
- 트리밍 구간: 00:00:00 ~ 00:02:00
- 트리밍 방식: **무손실 스트림 복사** (`ffmpeg -c copy`) — 재인코딩 없음, 화질 손실 없음
- 원본 길이: 1056.42초 (약 17분 36초)

## 생성 방법

```bash
cd 171204_pose1/171204_pose1
python trim_hd_videos.py
```

의존성: `imageio-ffmpeg` (`pip install imageio imageio-ffmpeg`)

## 메타데이터

상세 메타데이터는 [`metadata.json`](metadata.json) 참조.

## 실험 활용 가이드

#29 기준으로 현재 보존한 카메라 쌍:

| 용도 | 카메라 쌍 | 파일 쌍 |
|------|-----------|---------|
| mirrored front-oblique 후보 검토 | `00_21` + `00_11` | `hd_00_21_2min.mp4` + `hd_00_11_2min.mp4` |

- 캘리브레이션 파라미터는 `../calibration_171204_pose1.json` 내 `cameras` 배열에서  
  `name` 필드가 대상 카메라 ID와 일치하는 항목의 `K`, `distCoef`, `R`, `t` 사용.
- 3D GT와 비교 시: `../hdPose3d_stage1_coco19/` 내 `body3DScene_*.json` 참조.

## 관련 이슈

- #29 [feat] 두 동영상 스켈레톤 추출 및 3D 합성 기반 실험
