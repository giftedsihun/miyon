# AGENTS.md — 하루 일본어 (Haru Japanese) 개발 가이드

이 문서는 AI 에이전트와 새 개발자가 이 코드베이스를 이해하고 안전하게 수정하기 위한 안내서입니다.
모든 파일 경로는 이 폴더(`miyon_fordev`) 루트 기준입니다.

---

## 1. 프로젝트 개요

**하루 일본어**는 Windows 데스크톱용 **완전 오프라인 일본어 학습 앱**입니다.
히라가나/가타카나부터 JLPT N5~N1 수준의 자체 구성 학습 자료를 제공합니다.

- GUI: **Tkinter** (Python 표준 라이브러리 전용, 별도 pip 패키지 불필요)
- 저장: **SQLite** (`progress.db`), SRS 간격복습(1·2·4·7·14·30·60일)
- 음성: 로컬 **ずんだもん (Zundamon)** TTS — AI 보이스는 이 PC에서만 동작
- 배포: PyInstaller EXE + Inno Setup 설치 프로그램 + 오프라인 음성 번들

**핵심 설계 원칙:**
- UI 레이어는 `japanese_study.py`의 앱 콜백으로만 작업을 위임하고, 로직은 순수 모듈로 분리.
- 학습 콘텐츠는 `content.py`에 전부 포함 → 오프라인.
- 음성은 실시간 TTS 대신 **미리 생성된 wav 캐시**를 우선 재생 → 서버 없이 즉시 발음.

---

## 2. 실행 방법

```bat
:: 앱 실행 (이 폴더의 venv 사용)
ttsclient\.venv\Scripts\python.exe japanese_study.py

:: 테스트
ttsclient\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"

:: GUI 스모크 테스트 (데스크톱 세션 필요, 21개 화면 렌더링)
ttsclient\.venv\Scripts\python.exe gui_smoke_test.py
```

> 왜 이 venv를 쓰는가? ttsclient 서버가 Python 3.10 + onnxruntime-gpu 등 고정 패키지를
> 요구합니다. `ttsclient\.venv` 안에 그 환경이 통째로 들어 있습니다.

---

## 3. 파일 구조 (역할과 의존 방향)

### 진입점 & 상태
| 파일 | 역할 |
|---|---|
| `japanese_study.py` | Tkinter 앱 셸. 앱 상태, 화면 전환 콜백, 퀴즈/복습 흐름, 음성 서버 오케스트레이션. `JapaneseStudyApp` 클래스. |
| `app_info.py` | 버전/릴리스 이름 상수. |

### 순수 로직 (UI 미의존 — 테스트 용이)
| 파일 | 역할 |
|---|---|
| `content.py` | **학습 콘텐츠 전부**: 가나, N5~N1 단어/한자/문법 카드, 독해 지문, 듣기 대화, 획순 안내. 여기를 수정하면 보이스 캐시 재생성이 필요. |
| `study_logic.py` | 학습 안내 문구, 계획 페이스, TTS 복구 단계. |
| `learning_services.py` | 학습 설정 검증, CSV 단어장 가져오기, 카드 상태, 모의고사 설정. |
| `progress_logic.py` | 진단·통계·오답 분석·복습 예측·피드백 요약. |
| `quiz_logic.py` | 문제 풀 생성, 독해/청해 안내, 모의고사 비교. |
| `quiz_session.py` | 퀴즈 진행 상태: 순서, 점수, 재도전, 타이머. |

### 저장
| 파일 | 역할 |
|---|---|
| `storage.py` | SQLite 진도, SRS 일정, 백업/복원, 내보내기/가져오기, 나의 단어장, 메모, 즐겨찾기. |

### 음성 (가장 중요 — 4장 참고)
| 파일 | 역할 |
|---|---|
| `tts_service.py` | 음성 백엔드 상수·헬퍼 전부: GPT-SoVITS 경로, **ttsclient** 상수, `voice_cache_path()`, `cached_voice()`, `ttsclient_generate_voice()`, 다운로드/검증, 엔드포인트 프라이버시. |
| `start_ttsclient_server.py` | ttsclient 서버를 백그라운드로 기동하는 독립 스크립트. |
| `generate_zundamon_wav.py` | 단일 문장 wav 생성 (서버 자동 기동 포함). |
| `generate_voice_cache.py` | **보이스 캐시 대량 생성기** (5장 참고). |
| `voice_cache/` | 생성된 wav 2098개. 파일명 = `sha1(텍스트\|속도).wav`. |

### UI 렌더러 (모두 `app` 객체를 인자로 받아 콜백 위임)
| 파일 | 역할 |
|---|---|
| `ui_screens.py` | 홈, 학습, 과정 선택, 계획, 문자, 나의 단어장, 즐겨찾기, 복습, 통계. |
| `ui_catalog.py` | 단어/한자/문법 카드: 검색·필터·즐겨찾기·메모·이어학습·현재카드퀴즈. |
| `ui_quiz.py` | 퀴즈 화면, 청해 재생 제어, 난이도 버튼. |
| `ui_practice.py` | 가나/한자 쓰기 캔버스, 획순 대화상자, 문장 만들기, 받아쓰기. |
| `ui_dialogs.py` | 화면 크기·대비, 백업/복원, **AI 음성 설정** 대화상자. |

### 빌드/배포 (참고용 — 대부분 CI 또는 로컬 명령)
`build_exe.ps1`, `build_installer.ps1`, `build_offline_voice_bundle.ps1`,
`packaging/harujapanese_installer.iss`, `HaruJapanese.spec`, `.github/workflows/release.yml`.

### 기타
`tests/` (73개 단위 테스트), `gui_smoke_test.py`, `README.md`, `PROJECT_STATUS.md`,
`THIRD_PARTY_NOTICES.md`, `requirements-dev.txt`.

---

## 4. 음성 시스템 (반드시 숙지)

### 4.1 백엔드 선택
설정 `db["zundamon_backend"]` 값에 따라 두 백엔드 중 하나를 씁니다.
기본값은 **`"ttsclient"`** 입니다.

| 백엔드 | 설명 | 기본 주소 |
|---|---|---|
| `ttsclient` (기본) | `w-okada/ttsclient` REST 서버. 번들 venv에서 실행. | `http://127.0.0.1:19000` |
| `gpt_sovits` | 이전 방식. GPT-SoVITS FastAPI 서버. 사용자가 별도 준비. | `http://127.0.0.1:9880` |

백엔드 분기 로직은 `japanese_study.py`의 `zundamon_backend()`,
`_speak_with_ttsclient()`, `_speak_with_gpt_sovits()`에 있습니다.

### 4.2 ttsclient 서버
- 서버 명령: `ttsclient\.venv\Scripts\python.exe -m ttsclient.main cui --launch_client False --no_cui False`
  (반드시 `ttsclient\` 폴더를 작업 디렉터리로)
- 포트 19000 고정. wav 생성 엔드포인트: `POST /api/tts-manager/operation/generateVoice`
- 서버가 실제 포트를 잡는 프로세스는 **AppData Python310의 자식 프로세스**일 수 있음
  (ttsclient.main이 내부적으로 서버를 재실행). 부모를 죽이면 자식도 함께 정리해야 함.
- 슬롯 구성은 `ttsclient\settings\tts_conf.json` (`current_slot_index: 3` = 즈단몬 v2 모델).
- 음성 캐릭터 슬롯 4(즈단몬), 참조 음성 슬롯 0. — `tts_service.py` 상수 참고.
- 한국어 입력 시 `ext_lib\eunjeon`(mecab 바인딩)이 필요하며, 이미 설치돼 있음.

### 4.3 ⭐ 보이스 캐시 (핵심 최적화)
`speak_japanese()`는 **먼저 wav 캐시를 확인**하고, 있으면 즉시 재생합니다.

```
speak_japanese(text, status, rate)
  └─ speed = db["zundamon_speed"] * (1 + rate/20)   // rate=-3 → 0.85(느리게)
  └─ cached = cached_voice(text, speed)
       └─ 있으면 → winsound.PlaySound(캐시wav) 후 종료   [서버 불필요]
       └─ 없으면 → speak_with_zundamon()               [실시간 TTS 폴백]
```

캐시 파일명 규칙 (`tts_service.py`):
```
voice_cache/<sha1(f"{text}|{speed:.2f}")>.wav
```
- 같은 텍스트라도 속도가 다르면(1.0 vs 0.85) 다른 파일.
- 파일명을 수동으로 바꾸면 매칭이 깨지므로 금지.

캐시에 없는 새 텍스트는 실시간 TTS로 폴백되므로 앱이 깨지지 않습니다.

### 4.4 엔드포인트 프라이버시
`endpoint_privacy_notice(url)`는 로컬(127.0.0.1/localhost/::1)이면 "로컬 요청"으로,
외부 URL이면 경고 문구를 반환합니다. 외부 주소 저장 시 `ui_dialogs.py`가 사용자 확인을 요구합니다.
테스트에서 강제 허용은 `endpoint_privacy_opt_out()`를 씁니다.

---

## 5. 보이스 캐시 재생성 (콘텐츠 수정 후)

`content.py`를 수정했으면 다음을 실행해 **누락된 wav만** 추가 생성합니다.

```bat
:: 1) ttsclient 서버 기동 (또는 이미 떠 있으면 생략)
cd ttsclient
.venv\Scripts\python.exe -m ttsclient.main cui --launch_client False --no_cui False

:: 2) 별도 창에서 캐시 생성 (이미 있는 파일은 건너뜀)
ttsclient\.venv\Scripts\python.exe generate_voice_cache.py
```

`generate_voice_cache.py` 동작:
- `collect_texts()` → `content.py`에서 발음 대상 텍스트 수집
  (단어 본체+예문, 한자, 문법 예문, 독해 지문, 듣기 대화, 가나 전부, 테스트 문구)
- 각 텍스트 × 속도(1.0, 0.85) → `voice_cache_path()` 계산
- 파일 있으면 스킵, 없으면 `ttsclient_generate_voice()`로 생성 후 저장
- 생성 로그: `voice_cache_build.log` (이 폴더에는 제외)

단일 문장만 만들려면:
```bat
ttsclient\.venv\Scripts\python.exe generate_zundamon_wav.py --text "こんにちは" --output out.wav
```

---

## 6. 데이터 흐름

- 학습 기록: `%USERPROFILE%\.haru_japanese\progress.db` (SQLite)
  - 환경변수 `HARU_DATA_DIR`로 위치 변경 가능 (테스트에서 임시 폴더 사용).
- `content.py`의 카드 튜플 형식:
  - 단어 `(일본어, 읽기, 뜻, 예문)`
  - 한자 `(한자, 읽기, 뜻, 예문단어)`
  - 문법 `(패턴, 설명, 예문)`
  - 독해 `(제목, 지문, 문제, 정답, 오답리스트)`
  - 듣기 `(대화문, 문제, 정답, 오답리스트)`
- 카드 ID 규칙: `{레벨}:{유형}:{색인}` 예) `N5:word:0`, `N5:listening:0`.
  청해 판별은 `":listening:"` 포함 여부.

---

## 7. 코딩 규칙

1. **`japanese_study.py` import는 `from tts_service import (...)`** 로 되어 있으며,
   새 헬퍼를 추가하면 이 import 목록에 넣어야 함.
2. UI 렌더러는 새 창을 직접 만들지 않고 `app.page()`/`app.card()`를 사용.
3. 저장·네트워크 작업은 반드시 `threading.Thread(daemon=True)`에서 실행하고,
   UI 갱신은 `app.after(0, ...)`로 메인 스레드에 위임. (`status.winfo_exists()`로 생존 확인)
4. 음성 재생은 `winsound.PlaySound(..., SND_ASYNC)`, 중지는 `stop_speech()`.
5. **주석은 한국어로 작성**하는 것이 이 프로젝트 관례.
6. 순수 로직(UI 미의존)은 `study_logic/quiz_logic/progress_logic/learning_services`에 배치하고
   테스트를 작성. UI 변경은 `gui_smoke_test.py`와 수동 확인.
7. 파일명 해시(`sha1(텍스트|속도)`) 규칙을 바꾸지 말 것 — 캐시가 전부 무효화됨.
8. 비밀키/개인 DB/생성물(dist, voice_cache, .venv)은 Git에 올리지 않음.

---

## 8. 테스트 & 검증

```bat
:: 단위 테스트 (73개)
ttsclient\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"

:: 문법 검사
ttsclient\.venv\Scripts\python.exe -m py_compile japanese_study.py tts_service.py ui_*.py *.py

:: GUI 스모크 (데스크톱 세션 필요)
ttsclient\.venv\Scripts\python.exe gui_smoke_test.py
```

테스트 모듈:
- `tests/test_database.py` — 저장·백업·SRS·가져오기/내보내기·메모·즐겨찾기·통계
- `tests/test_diagnostic.py` — 콘텐츠·순수로직·TTS 소스/경로·설정
- `tests/test_quiz_session.py` — 퀴즈 상태·헤드리스 UI import 계약

---

## 9. 흔한 작업 예시

| 작업 | 하면 되는 것 |
|---|---|
| 단어 추가 | `content.py`의 해당 레벨 `words` 리스트에 튜플 추가 → 보이스 캐시 재생성 |
| 발음만 미리 다 만들기 | `generate_voice_cache.py` 실행 |
| 새 텍스트가 서버에서 생성 안 됨 | ttsclient 서버가 19000에 떠 있는지 확인 (`/docs` 응답) |
| 백엔드 바꾸기 | 홈 → AI 음성 설정 → 음성 엔진 콤보박스 (gpt_sovits/ttsclient) |
| 음성 설정 UI 구조 바꾸기 | `ui_dialogs.py`의 `show_voice_settings` (저장 로직 포함) |
| 앱 재빌드 | `build_exe.ps1` |

---

## 10. 주의 (알려진 함정)

- **VRAM 4GB**: 모델 로딩이 첫 요청에 수 분 걸림. slot 3(즈단몬 v2)이 기본.
- 서버 포트 19000이 AppData Python 자식 프로세스에 잡히는 경우가 있음 → 프로세스 트리 통째로 정리.
- `pkg_resources`는 `setuptools<81`로 고정돼 있어야 eunjeon(한국어 발음)이 동작.
- `voice_cache` 파일명을 절대 수동 변경 금지.
- `content.py`의 문법 예문에는 괄호 안 한국어가 포함될 수 있으나, wav는 일본어 전체 문자열을 그대로 생성.
