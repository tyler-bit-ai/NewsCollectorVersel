# Migration Inventory

## Source Project
- Legacy source: `C:\Codex\0219_NewsCollectorV2 (2)`
- Target project: `C:\Codex\NewsCollector_Versel`
- Migration goal: Vercel에서 매일 오전 9시(KST) 자동 실행되는 뉴스 수집, AI 분석, 메일 발송 파이프라인 구축

## Verified Findings
- `main.py`는 `collect_articles`, `collect_external_alerts`, `analyze_articles`, `send_report`, `send_safety_alert_notification`, `main`으로 전체 파이프라인을 구성한다.
- `config/settings.py`는 `.env`에서 API, OpenAI, Gmail 관련 필수 환경 변수를 로드한다.
- `notifiers/smtp_sender.py`는 `smtp.gmail.com:465`에 `SMTP_SSL`로 연결해 메일을 발송하고, 실패 시 `output/backups`에 HTML 백업 파일을 쓴다.
- `notifiers/web_generator.py`는 `output/web/daily_report.html`과 `output/web/history/*.html`을 생성한다.
- `utils/logger.py`는 `output/logs/news_collector_YYYYMMDD.log` 파일을 생성한다.
- `web/routes.py`와 `start_web.py`는 Flask 대시보드, 백그라운드 분석 실행, 수신자 관리, 리포트 조회 기능을 제공한다.

## Reuse Classification

### Reuse As-Is or With Minimal Import Path Changes
- `collectors/`
  - `naver_collector.py`
  - `google_collector.py`
  - `mofa_0404_collector.py`
  - 이유: 핵심 수집 책임이 분리되어 있고, 웹 UI와 직접 결합되어 있지 않다.
- `filters/`
  - `time_filter.py`
  - `keyword_filter.py`
  - `deduplicator.py`
  - 이유: 순수 파이프라인 처리 로직이며 Vercel 구조와 충돌하지 않는다.
- `analyzers/`
  - `summarizer.py`
  - `insight_generator.py`
  - 이유: OpenAI 호출 기반 분석 로직으로, 엔트리포인트만 바꾸면 재사용 가능하다.
- `utils/`
  - `exceptions.py`
  - `helpers.py`
  - `retry.py`
  - `time_windows.py`
  - 이유: 공통 유틸이며 파일 기반 상태 저장 의존성이 없다.
- `config/categories.yaml`
  - 이유: 수집 키워드/카테고리 정의로 재사용 가치가 높다.
- `notifiers/email_formatter.py`
  - 이유: 자동 메일 발송 목표와 직접 연결되며, 기존 메일 화면 구성을 최대한 유지해야 한다.

### Reuse With Required Changes
- `main.py`
  - 변경 필요: CLI 중심 진입점 대신 재사용 가능한 파이프라인 함수로 분해 필요
  - 변경 필요: 웹 페이지 생성 호출 제거
  - 변경 필요: Vercel 엔드포인트에서 호출 가능한 결과 객체 반환 구조로 변경
- `config/settings.py`
  - 변경 필요: Vercel용 환경 변수 구조 반영
  - 변경 필요: `EMAIL_RECIPIENTS` 레거시 구조 대신 `REPORT_RECIPIENTS`, 선택적 `SAFETY_ALERT_RECIPIENTS`, `ENABLE_0404_ALERTS`, `DRY_RUN`, `CRON_SECRET` 등 자동 실행 중심 계약 반영
- `notifiers/smtp_sender.py`
  - 변경 필요: `output/backups` 파일 백업 제거
  - 변경 필요: 실패 시 예외 또는 구조화된 오류 반환으로 대체
- `utils/logger.py`
  - 변경 필요: `output/logs` 파일 기록 제거 또는 콘솔/표준 로깅 중심으로 재구성
  - 이유: Vercel 서버리스에서 파일 로그 영속성이 보장되지 않음
- `config/recipient_store.py`
  - 변경 가능성: 웹 대시보드용 수신자 영속 관리 방식은 제거 가능
  - 대체 방향: 환경 변수 기반 수신자 목록 또는 단순 설정 파일

### Exclude From Migration
- `web/`
  - 제외 이유: 사용자 요구사항상 대시보드 불필요
  - 제외 근거: Flask API, 백그라운드 task, 리포트 HTML 목록 제공은 자동 발송 구조와 직접 관련 없음
- `start_web.py`
  - 제외 이유: Flask 대시보드 실행 전용 진입점
- `notifiers/web_generator.py`
  - 제외 이유: `output/web` 파일 생성 및 HTML 아카이브는 Vercel 자동 메일 발송 목표와 충돌
- `output/` 기반 산출물 전체
  - 제외 이유: 서버리스 환경에서 파일 영속성 불가
  - 영향 범위: `output/web`, `output/backups`, `output/logs`
- 웹 대시보드 관련 README 섹션, 이미지, 리포트 브라우징 동선
  - 제외 이유: 운영 방식이 완전히 달라짐

## Vercel Compatibility Notes
- Vercel Cron은 UTC 기준이므로 KST 오전 9시 실행은 `UTC 00:00`으로 설정해야 한다.
- 한국은 DST를 사용하지 않으므로 `UTC 00:00 = KST 09:00` 매핑이 고정된다.
- 서버리스 함수는 로컬 파일을 영구 저장할 수 없으므로 로그, 백업 HTML, 웹 리포트 아카이브에 의존하면 안 된다.
- 메일 발송은 SMTP 유지가 가능하지만, 실패 시 파일 백업이 아닌 예외 처리와 Vercel 로그 확인 방식으로 바꿔야 한다.
- 엔드포인트는 오케스트레이션만 담당하고, 수집/분석/포맷/발송은 `src/` 내부 공유 모듈로 유지하는 구조가 적합하다.

## 0404 Alert Decision Point
- 현재 레거시 파이프라인은 일반 일일 리포트 외에 `external_alerts`가 있을 경우 별도 `safety alert` 메일을 보낸다.
- 새 프로젝트에서 결정해야 할 항목:
  - 유지: 기존처럼 별도 메일 발송
  - 옵션화: `ENABLE_0404_ALERTS` 또는 별도 수신자 설정이 있을 때만 발송
  - 제외: 기본 뉴스 메일만 남기고 0404 전용 메일 제거
- 권장 방향:
  - 1차 구현에서는 옵션화가 가장 안전하다.
  - 이유: 기존 가치를 보존하면서도 Vercel 실행 시간과 운영 복잡도를 제어할 수 있다.

## Implementation Contract For Next Tasks
- 새 프로젝트는 `src/collectors`, `src/filters`, `src/analyzers`, `src/notifiers`, `src/utils`, `src/config`, `src/pipeline` 구조를 우선한다.
- 메일 발송 전용 프로젝트이므로 `WebGenerator`, Flask routes, dashboard templates/static assets는 만들지 않는다.
- README, `.env.example`, `vercel.json`, settings 모듈은 항상 같은 계약을 공유해야 한다.

## Migration Outcome Snapshot
- 실제 구현 기준으로 `src/pipeline/daily_job.py`가 자동 실행 오케스트레이터 역할을 수행한다.
- `api/cron.py`와 `vercel.json`이 Vercel Cron 진입점을 제공한다.
- 0404 알림은 제거되지 않았고, `ENABLE_0404_ALERTS` 및 `SAFETY_ALERT_RECIPIENTS`로 옵션화되었다.
