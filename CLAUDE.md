# Claude Instructions

## 시작 시 필수 작업

대화 시작 시 항상 `AGENTS.md`를 먼저 읽고, 해당 지침을 따를 것.

## 실행 전 필수 체크

파일을 수정하거나 생성하거나 삭제하는 작업을 시작하기 전에 반드시 다음을 확인한다:

1. 이 작업이 추적 중인 이슈의 작업 단위인가?
   - 그렇다면 해당 관리 문서(`docs/issues/` 아래)를 열고, 작업 로그 갱신 대상인지 확인한다.
2. 규모가 작아 보여도 예외로 처리하지 않는다. "단순 수정"도 커밋 단위 작업이면 로그 대상이다.
3. 위 판단이 불확실하면 `docs/agent-workflow/documentation-rules.md`를 읽고 결정한다.
4. 이 체크는 대화 시작 시 `AGENTS.md`를 한 번 읽은 것으로 대체되지 않는다. 파일 변경 직전에 다시 적용해야 한다.
5. 예외는 파일 변경이 전혀 없는 순수 질의응답뿐이다.

## 지침 우선순위

`AGENTS.md`에 명시된 규칙은 기본 동작보다 우선 적용된다.

---

# Behavioral Guidelines

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
