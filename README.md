# NewsCollector Vercel

Vercel에서 매일 오전 9시(KST)에 자동 실행되어 뉴스 수집, AI 분석, 메일 발송을 수행하는 Python 기반 파이프라인 프로젝트입니다.

## Current Scope
- 기준 구현: `C:\Codex\0219_NewsCollectorV2 (2)`
- 유지 목표: 뉴스 수집 로직, AI 분석 흐름, 메일 HTML 구성
- 제외 범위: Flask 대시보드, 웹 리포트 HTML 저장, 로컬 파일 백업/로그 아카이브
- 0404 해외 안전 공지: 기본적으로 `ENABLE_0404_ALERTS=true`일 때 옵션 형태로 수집 및 별도 메일 발송

## Planning Artifacts
- 프로젝트 규칙: [`shrimp-rules.md`](./shrimp-rules.md)
- 이관 범위 문서: [`migration_inventory.md`](./migration_inventory.md)

## Planned Runtime
- 배포 환경: Vercel
- 실행 방식: Vercel Cron + Python serverless function
- 목표 스케줄: 매일 `KST 09:00` (`UTC 00:00`)
- 공식 Vercel Cron 설정: `vercel.json`의 `/api/cron` 경로를 매일 `0 0 * * *`로 호출
- 요청 보호: Vercel 공식 권장 방식인 `CRON_SECRET`을 사용하고, 함수는 `Authorization: Bearer <CRON_SECRET>` 헤더를 검증

## Project Structure
```text
api/
  cron.py                 Vercel cron entrypoint
src/
  analyzers/              OpenAI 요약/인사이트 로직
  collectors/             Naver, Google, 0404 수집기
  config/                 settings.py, categories.yaml
  filters/                시간/키워드/중복 제거
  notifiers/              email formatter, SMTP sender
  pipeline/               core 수집/분석, daily_job orchestration
  utils/                  예외, helper, retry, logger, time window
tests/                    외부 API 비의존 단위 테스트
```

## Reused And Omitted Legacy Modules
- 재사용:
  - `collectors/`
  - `filters/`
  - `analyzers/`
  - `utils/exceptions.py`, `utils/helpers.py`, `utils/retry.py`, `utils/time_windows.py`
  - `config/categories.yaml`
  - `notifiers/email_formatter.py` 및 메일 템플릿
- 수정 후 재사용:
  - `main.py` 역할은 `src/pipeline/core.py`, `src/pipeline/daily_job.py`로 분리
  - `utils/logger.py`는 파일 로그 대신 콘솔 로그로 변경
  - `notifiers/smtp_sender.py`는 파일 백업 제거, dry-run 지원 추가
  - `config/settings.py`는 Vercel용 환경 변수 계약으로 재작성
- 제외:
  - `web/`
  - `start_web.py`
  - `notifiers/web_generator.py`
  - `output/web`, `output/backups`, `output/logs`

## Environment Variables
- 필수 API 키: `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `GOOGLE_API_KEY`, `SEARCH_ENGINE_ID`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`
- 메일 발송: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `REPORT_RECIPIENTS`
- 선택 항목: `SAFETY_ALERT_RECIPIENTS`, `ENABLE_0404_ALERTS`, `DRY_RUN`, `DEBUG_MODE`
- 실행 제어: `TIME_WINDOW_HOURS`, `MAX_ARTICLES_PER_CATEGORY`, `EMAIL_TOP_N`, `EMAIL_SUMMARY_MAX_CHARS`, `CRON_SECRET`

## Local Bootstrap
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

현재 `run.py`는 `src.pipeline.daily_job.run_daily_job()`을 호출하는 로컬 진입점입니다.

## Execution Flow
1. `src.pipeline.core.collect_articles()`가 카테고리별 뉴스를 수집합니다.
2. `TimeFilter`, `KeywordFilter`, `Deduplicator`가 기사 품질을 정리합니다.
3. `Summarizer`, `InsightGenerator`가 OpenAI 기반 요약과 인사이트를 생성합니다.
4. `EmailFormatter`가 기존 메일 레이아웃을 유지한 HTML을 만듭니다.
5. `SMTPSender`가 일일 리포트를 발송합니다.
6. `ENABLE_0404_ALERTS=true`이면 0404 공지를 추가 수집하고, 수신자가 있을 때 별도 알림 메일을 발송합니다.

## Validation Commands
```powershell
python -m unittest discover -s tests -v
python run.py
```

`python run.py`는 실제 환경 변수와 외부 API 키가 준비된 경우에만 전체 수집/분석/메일 흐름을 실행합니다. 테스트는 외부 API 없이도 핵심 계약을 검증합니다.

## Deploy To Vercel
1. Vercel 프로젝트를 이 디렉터리와 연결합니다.
2. Project Settings > Environment Variables에 `.env.example`의 값을 등록합니다.
3. 특히 `CRON_SECRET`은 16자 이상 랜덤 문자열로 설정합니다.
4. production 배포를 수행합니다.
5. 배포 후 Vercel Dashboard의 Cron Jobs에서 `/api/cron`이 `0 0 * * *`로 등록되었는지 확인합니다.
6. 필요하면 `Authorization: Bearer <CRON_SECRET>` 헤더로 `/api/cron`을 수동 호출해 정상 응답을 확인합니다.

## Vercel Cron Notes
- Vercel은 cron 요청을 production deployment에만 보냅니다.
- 공식 문서 기준 cron은 지정한 `path`로 `GET` 요청을 보냅니다.
- 한국은 DST를 사용하지 않으므로 `UTC 00:00`은 항상 `KST 09:00`입니다.
- 로컬에서는 동일 엔드포인트 계약을 직접 호출해 재현할 수 있습니다.
- Vercel은 실패한 cron 호출을 자동 재시도하지 않으므로, 실패 시 Runtime Logs를 확인해야 합니다.
- Cron은 중복 호출 가능성이 있으므로 메일 중복 발송 위험이 있으면 향후 idempotency 또는 lock 전략을 추가하는 것이 좋습니다.

## 0404 Alert Behavior
- `ENABLE_0404_ALERTS=true`이면 0404 게시판 키워드 매칭 공지를 수집합니다.
- 공지가 1건 이상 있고 `SAFETY_ALERT_RECIPIENTS`가 설정되어 있으면 별도 메일을 발송합니다.
- `SAFETY_ALERT_RECIPIENTS`가 비어 있으면 0404 공지는 수집만 하고 별도 메일은 건너뜁니다.
- `ENABLE_0404_ALERTS=false`이면 0404 수집과 별도 메일 모두 비활성화됩니다.

## Failure Handling
- SMTP 발송 실패 시 로컬 HTML 백업 파일은 만들지 않습니다.
- 실패 내용은 예외와 표준 로그로 노출되며, Vercel에서는 Runtime Logs에서 확인해야 합니다.
- cron 엔드포인트(`/api/cron`)는 실패 시 `500`과 오류 메시지를 반환합니다.

## Manual Endpoint Reproduction
로컬에서 Vercel 엔드포인트 계약을 검증할 때는 테스트 코드처럼 엔트리포인트 클래스를 호출해 확인할 수 있습니다. 운영에서는 Vercel이 `/api/cron`에 `Authorization: Bearer <CRON_SECRET>` 헤더를 붙여 호출합니다.
