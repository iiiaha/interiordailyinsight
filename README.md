# 인테리어 인사이트 위클리

인테리어 디자이너와 시공 업체를 위한 AI 기반 주간 트렌드 리포트 서비스.

## 아키텍처

```
네이버 검색 API → 수집 → 전처리 → Claude AI 분석 → HTML 리포트 → SendGrid 발송
                                                                    ↓
                                                              Supabase (구독자/리포트 저장)
```

## 기술 스택

| 영역 | 기술 |
|------|------|
| 데이터 수집 | 네이버 검색 API (cafearticle) |
| AI 분석 | Claude API (claude-sonnet-4-20250514) |
| 이메일 | SendGrid |
| 데이터베이스 | Supabase (PostgreSQL) |
| 언어 | Python 3.11+ |

## 설치

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 실제 API 키 입력
```

## Supabase 설정

1. [Supabase](https://supabase.com) 프로젝트 생성
2. SQL Editor에서 `db/schema.sql` 실행
3. `.env`에 `SUPABASE_URL`, `SUPABASE_KEY` 입력

## 실행

```bash
# 로컬 실행 (즉시 파이프라인 실행)
python scheduler/lambda_handler.py
```

## 테스트

```bash
pytest tests/ -v
```

## 파일 구조

```
interior-insight/
├── config/settings.py          # 환경변수 및 설정
├── collector/naver_collector.py # 네이버 API 데이터 수집
├── processor/text_processor.py  # 텍스트 전처리 및 스팸 필터
├── analyzer/claude_analyzer.py  # Claude AI 인사이트 분석
├── report/
│   ├── generator.py             # HTML 리포트 생성
│   └── templates/               # Jinja2 이메일 템플릿
├── mailer/sendgrid_mailer.py    # SendGrid 이메일 발송
├── db/
│   ├── schema.sql               # DB 스키마
│   └── supabase_client.py       # Supabase 클라이언트
├── scheduler/lambda_handler.py  # 메인 파이프라인
└── tests/                       # 테스트
```

## AWS Lambda 배포

```bash
# 패키지 빌드
pip install -r requirements.txt -t package/
cp -r config collector processor analyzer report mailer db scheduler package/
cd package && zip -r ../deploy.zip . && cd ..

# Lambda 함수 생성 후 deploy.zip 업로드
# 핸들러: scheduler.lambda_handler.handler
# 타임아웃: 300초 (5분)
# 메모리: 512MB
# EventBridge 규칙으로 매주 월요일 9시 트리거
```
