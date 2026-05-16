# docs/

이 디렉토리는 rack-venture 프로젝트의 모든 문서를 담는다.

## 구조

```
docs/
├── README.md              — 이 파일. 문서 디렉토리 인덱스
├── onboarding.md          — 팀원 로컬 환경 세팅 가이드
├── mvp-v2/                — rack-venture 전용 MVP v2 문서 (신규 작업은 여기에)
├── agent-workflow/        — 에이전트·기여자 워크플로우 규칙
├── issues/                — rack-venture 이슈 관리 문서
└── archive/               — 구 레포(rack-tracker-forked) 마이그레이션 아카이브
    ├── mvp-v1/            — 구 레포 MVP v1 문서
    └── mvp-v2/            — 구 레포 MVP v2 문서
```

## 각 폴더 역할

| 경로 | 역할 |
|------|------|
| `mvp-v2/` | rack-venture 전용 MVP v2 설계·기능 문서 |
| `agent-workflow/` | 브랜치·커밋·PR·문서화 워크플로우 규칙 |
| `issues/` | GitHub 이슈와 1:1 대응하는 작업 관리 문서 |
| `archive/` | 참고용 아카이브. 수정하지 않는다. 이슈 번호는 구 레포 기준 |

## 신규 문서 작성 시

- 기능·설계 문서 → `docs/mvp-v2/` 아래
- 이슈 관리 문서 → `docs/issues/{type}/{N}-{slug}.md`
- 워크플로우 규칙 변경 → `docs/agent-workflow/` 아래
