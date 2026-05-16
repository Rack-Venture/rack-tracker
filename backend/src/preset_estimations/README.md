# Preset Estimation JSON

이 디렉토리에 미리 추출한 PoseLandmarker 추정 결과 JSON을 저장합니다.

## 파일 명명 규칙

`{preset_id}.json` — 예: `hd_00_21_2min.json`, `hd_00_11_2min.json`

## JSON 형식 (`preset_estimation.v1`)

```json
{
  "schemaVersion": "preset_estimation.v1",
  "presetId": "hd_00_21_2min",
  "videoInfo": {
    "fps": 29.97,
    "width": 1920,
    "height": 1080,
    "frameCount": 3596
  },
  "frames": [
    {
      "frameIndex": 0,
      "timestampMs": 0.0,
      "poseDetected": true,
      "landmarks": [
        {
          "name": "nose",
          "x": 0.512,
          "y": 0.243,
          "z": -0.021,
          "visibility": 0.998,
          "presence": 0.999
        }
      ]
    }
  ]
}
```

## 필드 설명

- `videoInfo.fps`: 원본 영상 프레임률
- `videoInfo.frameCount`: 전체 프레임 수 (없으면 생략 가능)
- `frames[].frameIndex`: 원본 영상에서의 프레임 인덱스
- `frames[].timestampMs`: 타임스탬프 (밀리초)
- `frames[].poseDetected`: 포즈 감지 여부
- `frames[].landmarks`: 33개 MediaPipe 랜드마크 (x, y, z는 정규화 좌표)
