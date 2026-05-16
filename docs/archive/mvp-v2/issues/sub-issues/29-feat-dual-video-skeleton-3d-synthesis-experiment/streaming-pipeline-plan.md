# [design] 듀얼 비디오 스켈레톤 추출 스트리밍 파이프라인 단계 문서
Parent: #29

## 문서 관계
- 이 문서는 `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md`의 파생 설계 문서다.
- 목적은 현재 구현된 스트리밍/청크 파이프라인의 실제 상태를 코드 기준으로 설명하고, 다음 구현 단계를 명확히 나누는 것이다.
- 이 문서에는 설계 판단, 단계 구분, 후속 구현 방향만 남긴다.
- 이슈 진행 로그와 커밋 단위 작업 이력은 부모 관리 문서에 기록한다.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## Implementation Status & Decision Matrix

| ID | 구분 | 레이어/단계 | 상태 | 결정된 방향 | 결정 필요 사항 | 다음 액션 | 참조 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| STR-01 | chunk 기반 frame streaming | video reader | 구현 완료 | 전체 프레임 일괄 적재 대신 `FrameChunk` 단위 producer/consumer 구조를 사용한다. | 없음 | chunk 크기와 queue maxsize 변경 시 문서와 stageDetails 예시를 함께 갱신한다. | 단계 1 |
| STR-02 | 내부 stage 분리 | pipeline orchestration | 구현 완료 | frame, pose, skeleton, benchmark stage를 분리해 bounded queue 기반으로 진행한다. | analysis/LLM 단계는 여전히 후반 finalize 경로다. | finalize 이전까지 어디를 streaming stage로 볼지 설명만 유지보수한다. | 단계 2 |
| STR-03 | artifact spooling | collector/output | 구현 완료 | skeleton과 benchmark 산출물을 JSONL/file-backed 방식으로 누적해 메모리 상주량을 줄인다. | 없음 | artifact 경로나 summary 필드가 바뀌면 synthesis handoff 문서와 함께 갱신한다. | 단계 3 |
| STR-04 | dual synthesis handoff | cross-plan dependency | 구현 완료 | 현재 3D 합성기는 pose chunk handoff가 아니라 completed 2D skeleton artifact를 읽는 batch stage로 연결한다. | chunk-level synthesis handoff는 아직 범위 밖이다. | artifact-level handoff를 기준선으로 유지하고 chunk-level synthesis는 별도 이슈로 분리한다. | 단계 D |
| STR-05 | progress/timing summary | observability | 구현 완료 | stageDetails와 pipeline summary로 streaming 진행 상태와 병목을 노출한다. | 없음 | frontend live progress와 benchmark summary가 같은 필드를 보고 있는지 주기적으로 확인한다. | 현재 상태에 대한 최종 판단 |
| STR-06 | 실시간 synthesis stream | future scope | 보류 | 첫 3D MVP에서는 batch/artifact 기반 synthesis를 우선한다. | 없음 | batch synthesis 검증 후 streaming 연결을 재평가한다. | 단계 D |

## 요약
현재 백엔드는 frame 읽기, pose inference, skeleton 수집, benchmark 수집을 분리한 bounded-queue 컨베이어를 가진다. 다만 analysis/LLM finalize와 실시간 3D synthesis handoff까지 모두 하나의 연속 스트림으로 연결된 구조는 아니다.

현재 코드가 실제로 하는 일은 다음과 같다.

1. 비디오를 읽어 `FrameChunk` 단위로 잘라 낸다.
2. frame producer 가 bounded frame queue 로 청크를 공급한다.
3. pose worker 가 frame queue 에서 청크를 꺼내 추론하고 pose queue 로 넘긴다.
4. skeleton collector 와 benchmark collector 가 pose queue 기반 산출물을 spool/file-backed artifact 로 누적한다.
5. 모든 청크 처리가 끝난 뒤 skeleton artifact, benchmark summary, analysis, LLM feedback 을 최종 결과로 정리한다.
6. completed job 의 skeleton artifact 는 이후 batch 3D synthesis stage 의 입력으로 재사용된다.

즉, 현재 구조는 "2D 추출용 4-stage bounded streaming + artifact handoff"이며, "실시간 3D synthesis까지 포함한 end-to-end streaming"은 아직 아니다.

## 배경
기존 구조는 다음 순서를 따르는 배치형 파이프라인이었다.

1. 비디오 업로드
2. 전체 프레임 추출
3. 전체 프레임 리스트를 대상으로 pose inference
4. 전체 inference 결과를 기준으로 skeleton / benchmark / analysis 생성

이 구조는 단일 비디오에서는 단순하지만, 듀얼 비디오를 병렬 실행할 때 메모리 사용량이 급격히 커진다. 실제로 1080p 두 영상을 동시에 돌릴 때 OpenCV 메모리 부족 오류가 발생했고, 이는 shared instance race 보다는 전체 프레임 일괄 적재에 더 가깝게 설명된다.

따라서 이 작업의 핵심 목표는 다음 두 가지다.

- 비디오 A, B를 병렬 실행하는 요구는 유지한다.
- 각 job이 전체 프레임을 메모리에 쌓지 않도록 바꾼다.

## 단계 1. 현재 구현의 정확한 타임라인

### 핵심 판단
현재 구현은 frame 읽기, pose 추론, skeleton collector, benchmark collector 가 분리된 스트리밍 구조다. 다만 analysis, LLM feedback, batch synthesis 는 completed artifact 이후 단계로 남아 있다.

### 현재 실행 순서
한 job 안에서 실제 흐름은 다음과 같다.

1. `JobManager._execute_pipeline()` 이 실행을 시작한다.
2. `VideoReaderService.iter_frame_chunks()` 기반 producer 스레드가 `FrameChunk` 를 생성해 frame queue 에 넣는다.
3. pose worker 가 frame queue 에서 청크를 꺼내 `PoseInferenceService.infer_chunk()` 로 처리한 뒤 pose queue 에 넣는다.
4. skeleton collector 가 pose queue 결과를 읽어 JSONL spool 과 skeleton artifact 로 누적한다.
5. benchmark collector 가 pose queue 결과를 읽어 frame metric spool 과 pipeline summary 를 누적한다.
6. 모든 queue 가 종료되면 skeleton artifact 와 benchmark artifact 를 finalize 한다.
7. 그 다음 `AnalysisPipelineService.analyze()` 와 LLM feedback 이 완료 artifact 를 기준으로 실행된다.
8. completed job 은 persisted skeleton artifact 와 benchmark summary 를 조회 가능 상태로 남긴다.

### 현재 구조를 한 줄로 표현하면
`FrameProducer + PoseWorker + SkeletonCollector + BenchmarkCollector + post-finalize analysis`

### 현재 코드에서 확인되는 지점
- `backend/service/job_manager.py`
  `FRAME_CHUNK_SIZE = 32`, `FRAME_CHUNK_QUEUE_MAXSIZE = 2`, `POSE_CHUNK_QUEUE_MAXSIZE = 2`, `COLLECTOR_QUEUE_MAXSIZE = 2`
- `backend/service/job_manager.py`
  `frame_queue`, `pose_queue`, `skeleton_queue`, `benchmark_queue`
- `backend/service/job_manager.py`
  skeleton / benchmark collector thread 시작과 queue 종료 처리
- `backend/service/job_manager.py`
  `skeleton_spool_path`, `benchmark_spool_path`, `load_skeleton_artifact()`
- `backend/service/job_manager.py`
  `pipeline_summary`, `stageDetails`
- `backend/service/video_reader.py`
  `iter_frame_chunks()`, `probe_metadata()`
- `backend/service/benchmarking.py`
  `PoseChunkBenchmarkCollector`

### 현재 구조의 의미
- 읽기 속도가 추론 속도보다 빠르면 queue 가 가득 차고 producer 가 기다린다.
- 읽기 속도가 추론 속도보다 느리면 consumer 가 다음 chunk 를 기다린다.
- 따라서 "대기 없이 쭉쭉 흐르는 구조"가 아니라 "필요 이상 버퍼링하지 않는 backpressure 구조"가 맞다.

## 단계 2. 현재 구조에서 진짜 스트리밍과 가짜 스트리밍 구분

### 2-1. 진짜 스트리밍인 부분

#### 프레임 전체 적재를 피한 점
기존에는 `extract_frames()` 가 `frames = list(self.iter_frames(...))` 로 전체 프레임을 메모리에 올렸다. 지금 주 경로는 `iter_frame_chunks()` 기반으로 동작하므로, 적어도 "전체 프레임 RGB 이미지 전체를 한 번에 보관"하는 구조는 벗어났다.

#### producer / consumer 사이 bounded queue
`JobManager._iter_bounded_frame_chunks()` 는 producer 스레드가 chunk 를 읽고, consumer 가 이를 꺼내 쓰는 구조다. queue 크기를 2로 제한해 버퍼가 무한정 커지지 않게 했다.

#### inference 직후 이미지 메모리 해제
`PoseInferenceService.infer_chunk()` 는 각 프레임 추론 직후 `frame.image = None` 으로 image reference 를 비운다. 이 덕분에 프레임 이미지 메모리는 chunk 처리 후 빠르게 회수될 수 있다.

### 2-2. 아직 batch/finalize 경로로 남아 있는 부분

#### analysis / LLM feedback 은 completed artifact 이후에 실행
2D 추출 자체는 stage 분리형이지만, `AnalysisPipelineService.analyze()` 와 LLM feedback 은 모든 collector 종료 후 실행된다. 즉 "업로드부터 최종 분석 결과까지 전 단계가 동시에 흐르는 구조"는 아니다.

#### 실시간 A/B synthesis handoff 는 아직 없다
현재 3D 합성기는 `DualVideoSynthesisCoordinator` 를 실시간으로 연결하지 않고, completed 2D skeleton artifact 를 `SkeletonArtifactRepository` 로 다시 읽는 batch stage 로 동작한다.

#### synthesis SSE 는 없다
합성 결과는 별도 `POST /synthesis/jobs` 로 생성하고 상태는 polling 기반으로 조회한다. 2D job 의 SSE와 달리 synthesis 전용 stream endpoint 는 아직 없다.

### 2-3. 결론
현재 구조를 정확히 표현하면 다음과 같다.

- 진짜 스트리밍:
  프레임 읽기, chunk 분할, bounded buffering, pose worker, collector thread, spool artifact, timing summary
- 아직 미완성:
  chunk 단위 downstream analysis, 실시간 A/B synthesis handoff, synthesis SSE

즉, 지금은 "2D 추출 컨베이어는 구현 완료, synthesis는 artifact handoff 기준 batch stage" 상태다.

## 단계 3. 완성형 컨베이어로 가기 위한 다음 구현 단계

### 목표 상태
완성형 컨베이어는 각 단계가 독립적인 책임과 bounded queue 를 갖고, 서로 backpressure 를 주고받으면서도 가능한 범위까지 겹쳐서 실행되는 구조여야 한다.

권장 stage 구분은 다음과 같다.

1. `FrameProducer`
2. `PoseWorker`
3. `SkeletonCollector`
4. `BenchmarkCollector`
5. `SynthesisCoordinator`
6. `ResultFinalizer`

### 3-1. 단계별 목표

#### 단계 A. 현재 1단계 스트리밍 안정화
목표:
- 현재 chunk 기반 경로를 기본 실행 경로로 안정화
- 단일 비디오와 듀얼 비디오 모두에서 메모리 폭증이 재발하지 않도록 검증

필요 작업:
- chunk 크기와 queue 크기 설정값을 환경 또는 설정 레벨에서 조정 가능하게 만들기
- 현재 진행률, 예외 처리, partial benchmark 생성 경로를 더 단단하게 다듬기
- 현재 skeleton 누적 및 frame metric 누적이 어느 정도 메모리를 쓰는지 계측하기

#### 단계 B. 진짜 내부 컨베이어 분리
목표:
- 읽기와 추론뿐 아니라, 추론과 skeleton 누적도 겹치게 만들기

필요 작업:
- `FrameChunk` queue 와 `PoseChunk` queue 를 분리
- reader worker, pose worker, collector worker 를 각각 독립 실행 단위로 분리
- job manager 는 직접 프레임을 처리하는 대신 stage orchestration 만 담당

이 단계가 되면 구조는 다음에 가까워진다.

`video read -> frame queue -> pose infer -> pose queue -> skeleton collect`

#### 단계 C. downstream incrementalization
목표:
- skeleton, benchmark, analysis 중 batch 성격이 강한 부분을 줄이기

필요 작업:
- skeleton 을 전부 메모리에 쌓는 대신 JSONL append 또는 chunk 파일 저장 검토
- benchmark summary 를 running aggregate 방식으로 전환
- analysis 가 전 프레임 완료 전에는 불가능한지, 일부 preview 성 정보라도 미리 만들 수 있는지 검토

이 단계가 완료되어야 "입력만 스트리밍"이 아니라 "출력까지 점진적으로 완성되는 파이프라인"에 가까워진다.

#### 단계 D. 듀얼 비디오 합성 컨베이어 연결
목표:
- video A 와 video B 의 `PoseChunk` 를 맞춰 3D synthesis 단계로 넘기기

필요 작업:
- `DualVideoSynthesisCoordinator` 를 실제 job orchestration 경로에 연결
- `chunk_index` 기준 pairing 이 충분한지, timestamp window pairing 이 필요한지 검토
- 한쪽 chunk 가 늦을 때 pending window 와 timeout 정책 정의
- A/B chunk pair 를 소비하는 synthesis worker 추가

이 단계가 되어야 비로소 "두 비디오가 각자 추론된 뒤, 대응되는 chunk 들이 바로 다음 절차로 넘어간다"는 표현이 성립한다.

### 3-2. 권장 구현 순서

1. 현재 chunk + bounded queue 경로를 기본 경로로 고정하고 안정화한다.
2. `FrameChunk -> PoseChunk` 사이를 독립 queue 로 분리한다.
3. `PoseChunk -> SkeletonCollector / BenchmarkCollector` 를 분리한다.
4. skeleton 과 benchmark 의 메모리 누적 방식을 줄인다.
5. `DualVideoSynthesisCoordinator` 를 orchestration 에 연결한다.
6. A/B aligned chunk pair 를 실제 synthesis service 로 전달한다.

### 3-3. 현재 코드 기준 후속 변경 중심 파일
- `backend/service/job_manager.py`
  현재 orchestration 중심. stage 분리가 가장 많이 들어갈 파일이다.
- `backend/service/video_reader.py`
  chunk 생성 정책과 producer 역할을 더 명확히 분리할 수 있다.
- `backend/service/pose_inference.py`
  chunk 단위 추론은 이미 있으므로 worker 화와 결과 handoff 경계가 다음 작업이다.
- `backend/service/skeleton_mapper.py`
  현재는 메모리 누적형 assembler 이므로 incremental persistence 방향이 필요하다.
- `backend/service/benchmarking.py`
  최종 결과 조립 위주에서 running aggregate 위주로 바뀌어야 한다.
- `backend/service/dual_video_synthesis_coordinator.py`
  구현은 존재하지만 orchestration 연결이 아직 없다.

## 현재 상태에 대한 최종 판단
- 현재 구현은 "완성된 컨베이어"가 아니다.
- 현재 구현은 "배치 파이프라인의 가장 큰 메모리 병목을 걷어내기 위한 1단계 스트리밍"이다.
- 읽기와 소비는 일부 겹칠 수 있지만, 모든 단계가 동시에 독립 실행되는 구조는 아니다.
- 프레임이 완전히 대기 없이 흐르는 구조도 아니다.
- 대신 bounded queue 기반 backpressure 로 메모리 상한을 잡는 구조다.
- 완성형 컨베이어라고 부르려면, 최소한 `FrameProducer -> PoseWorker -> SkeletonCollector -> SynthesisCoordinator` 가 독립 stage 로 연결되어야 한다.

## 참고 코드
- `backend/service/job_manager.py`
- `backend/service/video_reader.py`
- `backend/service/pose_inference.py`
- `backend/service/skeleton_mapper.py`
- `backend/service/dual_video_synthesis_coordinator.py`
- `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md`
