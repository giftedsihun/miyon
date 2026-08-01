# 하루 일본어

완전 초보부터 JLPT N1 수준까지 이어지는 오프라인 Windows 일본어 학습 앱입니다.

현재 버전: `1.0.0 Learning Journey`

배포 변경점은 `RELEASE_NOTES.md`에서 확인할 수 있습니다.

> 이 저장소의 학습 자료는 자체 구성한 교육용 자료입니다. 공식 JLPT 기출문제나
> 공식 출제 범위를 그대로 재현하지 않습니다.

포함 기능:

- 히라가나·가타카나 기본 46자, 탁음·반탁음·요음, 촉음·장음 규칙 학습
- N5~N1 수준별 자체 구성 단어, 한자, 문법 카드와 예문
- 여행·드라마·업무에서 만난 표현을 직접 저장하고 기존 SRS 복습·퀴즈로 익히는 나의 단어장
- `word,reading,meaning,example` 형식 CSV로 나의 단어장을 한 번에 가져오기
- 카드 검색·품사·즐겨찾기 필터 결과만으로 바로 확인 퀴즈
- 과정과 무관하게 저장한 단어·한자·문법을 한곳에서 관리하고 바로 푸는 즐겨찾기 보관함
- 단어·한자·문법 카드별 개인 메모 저장, 메모 검색과 메모 카드만 빠른 필터링
- 직접 과정 선택 또는 구간별 결과·다음 학습 안내를 제공하는 12문항 균형 진단
- 단어·한자·문법·문자 혼합 퀴즈, 정답 직후 예문·핵심 설명 피드백, 자동 오답 기록과 완료 직후 오답 다시 풀기
- 단계별 짧은 독해와 대본 숨김·느린 속도 반복 재생 청해 연습, 맞힌 지문을 기억하는 이어 풀기, 영역별 결과·다음 학습 안내를 제공하는 12문항 종합 모의고사
- 문항 수와 제한 시간을 조절해 실제처럼 집중할 수 있는 JLPT 스타일 시간 제한 모의고사와 영역별 결과 분석
- 최근 모의고사와 정확도를 비교하고, 영역별 결과·해설·오답 재도전까지 이어지는 시험 복습
- 로컬 ずんだもん Speech WebUI AI 음성으로 예문과 청해 대화 재생
- AI 음성 설정에서 설치 파일·모델 준비 현황, 복구 단계와 로그 위치를 한눈에 진단
- 히라가나·가타카나 입력 확인 쓰기 연습, 한자 참고 획순 안내, 마우스·터치 필기 칸과 획 수 기록
- 정답 뒤 난이도 선택을 반영하는 1·2·4·7·14·30·60일 간격 복습과 일일 학습, 연속 학습, 정답률 통계
- 오늘부터 7일간의 복습량 예측과 오늘 복습 우선 시작 버튼
- 설정 가능한 세션별 복습 상한으로 과부하 없이 예정 복습 이어가기
- 예정 복습과 일일 목표를 우선순위로 안내하고 하루 동안 숨길 수 있는 홈 리마인더
- Windows DPI에 맞춰 자동 조절되며 필요 시 80~140%로 직접 지정 가능한 화면 읽기 크기
- 오답과 정확도를 바탕으로 약한 학습 유형으로 바로 이어지는 홈 집중 연습
- 단어 뜻·문법 빈칸·독해 근거·청해 핵심 정보처럼 오답 원인을 세분화해 분석하고 해당 문제만 집중 연습
- 오답 원인별 자료 확인, 학습 화면 이동, 집중 문제 풀이를 잇는 회복 경로
- 기본 Windows DPI 화면과 선택 가능한 고대비 색상 대비 설정
- 과정 변경 뒤에도 이전 과정의 즐겨찾기와 예정 복습을 안전하게 이어서 출제
- 학습 계획에 맞춰 순서대로 제공되는 오늘의 단어·문법 코스와 하루 한 번의 코스 완료 기록
- 최근 7일 학습 리듬, 학습 이정표, 최근 퀴즈 정확도 흐름·기록, 영역별 시험 기록과 과정별 카드 숙련도
- SQLite 기반 완전 오프라인 학습 기록 저장
- 최근 14일 자동 백업, 수동 백업과 안전한 학습 기록 복원
- 진도·단어장·메모·즐겨찾기·설정을 다른 PC로 옮기는 버전 검증 학습 기록 묶음 내보내기/가져오기
- 단어·한자·문법 카드는 과정별 마지막 위치를 기억해 다음에 이어서 학습
- 모든 카드에 학습 전·학습 중·안정적 암기 상태와 유형별 안정 암기 진행 막대를 표시하고, 상태별 카드만 필터링
- 학습 계획에서 과정별 새·학습 중·안정 카드 수와 다음 학습 안내를 확인하고, 상태별 단어·한자·문법 확인 퀴즈 바로 시작
- 카드마다 예문 낭독·한자 쓰기·문법 바꿔 말하기 같은 짧은 능동 회상 안내와 목표 일정 대비 학습 페이스 제공
- 통계 화면에서 활동·복습·퀴즈 기록을 Excel 호환 CSV로 내보내기

## 실행

### 필요 환경

- Windows 10/11
- Python 3.14 (Tkinter 포함). 기본 학습 기능은 Python 표준 라이브러리만 사용합니다.
- EXE 빌드에는 `requirements-dev.txt`의 PyInstaller가 필요하며, 빌드 스크립트가 자동으로 설치합니다.

```powershell
python japanese_study.py
```

## EXE 만들기

PowerShell에서 실행합니다.

```powershell
.\build_exe.ps1
```

완성된 파일은 `dist\HaruJapanese.exe`에 생성됩니다.

빌드 전에 자동 회귀 테스트가 실행됩니다. 테스트만 실행하려면 다음 명령을 사용합니다.

```powershell
python -m unittest discover -s tests -v
```

데스크톱 세션이 있는 Windows에서 모든 주요 화면이 오류 없이 렌더링되는지 확인하려면 다음을 실행합니다. 21개 화면을 모두 띄운 뒤 0이 아닌 종료 코드로 실패를 알립니다.

```powershell
python gui_smoke_test.py
```

## 설치 프로그램 만들기

[Inno Setup 6](https://jrsoftware.org/isinfo.php)가 설치된 PC(winget: `winget install JRSoftware.InnoSetup`)에서 다음을 실행하면 EXE와 함께 `dist\installer\HaruJapaneseSetup-{버전}.exe` 설치 프로그램과 SHA-256 체크섬 목록이 생성됩니다.

```powershell
.\build_installer.ps1 -SkipExeBuild
```

배포용으로 서명하려면 코드 서명 인증서를 지정합니다.

```powershell
.\build_installer.ps1 -CertificatePath "C:\path\to\cert.pfx" -CertificatePassword "****"
```

서명에는 `signtool`(Windows SDK)이 사용되며, 타임스탬프 서버 기본값은 DigiCert입니다. 서명 후 `Get-AuthenticodeSignature`로 유효성을 검사합니다. `v*` 태그를 푸시하면 `.github/workflows/release.yml`이 테스트·EXE·설치 프로그램·체크섬을 만들어 GitHub Release에 자동 첨부합니다.

검증 참고: Inno Setup을 winget으로 설치하면 `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`에 설치되는데, `build_installer.ps1`이 이 경로를 자동으로 찾습니다. 인증서 없이 실행하면 경고와 함께 서명 없이 빌드되며, `Get-AuthenticodeSignature` 상태가 `NotSigned`로 표시됩니다.

학습 진도는 사용자 폴더의 `.haru_japanese\progress.db`에 저장되므로 프로그램을 다시 실행해도 단계 선택, 퀴즈 결과, 오답 노트가 유지됩니다.

통계 화면의 `백업 및 복원 관리`에서 현재 기록을 직접 백업하거나 이전 백업을 복원할 수 있습니다. 앱은 하루에 한 번 `.haru_japanese\backups\automatic`에 최근 14일치 백업을 보관하며, 복원 직전에는 현재 기록도 별도로 백업합니다.

같은 화면의 `기록 내보내기`는 모든 학습 데이터를 하나의 `.zip` 묶음으로 만듭니다. 다른 PC에서는 `기록 가져오기`로 복원할 수 있으며, 가져오기 전 현재 기록은 자동 백업됩니다.

통계 화면의 `CSV 내보내기`는 활동 일자, 복습 상태, 퀴즈 결과를 하나의 UTF-8 CSV 파일로 저장합니다. Excel에서 열 수 있으며, CSV는 분석용 사본이므로 앱에 다시 가져오지는 않습니다.

`나의 단어장`의 `CSV 가져오기`는 UTF-8 CSV의 첫 줄에 `word,reading,meaning` 열을 요구하며 `example` 열은 선택입니다. 같은 일본어와 읽기가 있으면 뜻과 예문을 갱신합니다.

학습 자료는 `content.py`에 포함되어 있습니다. 이 앱의 자료는 오프라인 학습을 위해 자체 구성한 과정이며, 공식 JLPT 기출문제나 공식 출제 범위를 그대로 재현한 자료는 아닙니다.

## 로컬 AI 음성 (ずんだもん Speech WebUI)

AI 음성은 [zunzun999/zundamon-speech-webui](https://github.com/zunzun999/zundamon-speech-webui)의 ずんだもん GPT-SoVITS 모델과, 모델과 호환되는 고정 [GPT-SoVITS API](https://github.com/zunzun999/GPT-SoVITS) 리비전을 사용합니다. 모델 서버는 내 PC에서만 실행하며 외부 클라우드 API나 API 키를 사용하지 않습니다.

1. 앱을 열거나 `발음 듣기`를 누르면 하루 일본어가 AI 서버 상태를 확인합니다. 서버가 꺼져 있으면 사용자 폴더의 `.haru_japanese\zundamon-gpt-sovits-api`에 Zundamon 모델과 호환되는 고정 GPT-SoVITS API 버전을 내려받고, 전용 Python 3.9 환경과 CPU용 실행 패키지를 준비합니다.
2. 이어서 ずんだもん 파인튜닝 모델과 필요한 GPT-SoVITS 추론 모델을 자동으로 내려받습니다. 첫 실행에는 수 GB의 파일과 패키지를 받아야 하므로 인터넷 속도에 따라 오래 걸릴 수 있습니다. 이때 앱을 닫지 마세요.
3. 준비가 끝나면 앱이 전용 환경에서 GPT-SoVITS FastAPI 서버를 자동 시작합니다. 모든 `발음 듣기`와 청해 재생은 이 하나의 ずんだもん AI 음성만 사용합니다.
4. 홈의 `AI 음성 확인/시작`에서 진행 상태를 다시 확인하거나 시작을 재시도할 수 있습니다. 설정 창의 `상태 새로고침`은 필수 도구와 로그 위치를 표시하며, `테스트 음성`으로 실제 API 요청과 WAV 재생까지 확인할 수 있습니다. 준비 또는 서버 시작 오류는 `.haru_japanese\zundamon-setup.log` 및 `.haru_japanese\zundamon-api.log`에 저장됩니다.

처음 설치하려면 `git`, `uv`, `ffmpeg`가 Windows PATH에 있어야 합니다. FFmpeg가 없다면 PowerShell에서 `winget install Gyan.FFmpeg`로 설치한 뒤 앱을 다시 열어 주세요. 앱은 누락된 도구를 설정 창과 음성 재생 실패 안내에 명확히 표시하고, 불완전하게 내려받은 모델 파일을 다시 받고, 고정 API 리비전과 맞지 않는 이전 설치는 다시 준비합니다.

기본 주소는 `http://127.0.0.1:9880`입니다. 앱은 고정된 GPT-SoVITS API의 `POST /` 엔드포인트로 `text`, `text_language: "ja"`, `speed`를 보내 일본어 WAV 오디오를 요청합니다. 외부 클라우드 API나 API 키를 사용하지 않습니다.

주소를 다른 HTTP(S) 서버로 바꾸면 발음 요청의 일본어 텍스트가 그 서버로 전송될 수 있습니다. 앱은 저장 전 경고를 표시하므로 신뢰하는 서버에서만 사용하세요. 모델 다운로드는 임시 파일로 받은 뒤 재시도하며, 제공되는 SHA-256 값이 있는 경우 검증할 수 있습니다.

이 앱은 Windows 일본어 음성을 사용하지 않습니다. 자동 시작은 기본으로 켜져 있으며, 필요하면 `AI 음성 설정`에서 끌 수 있습니다. 쓰기 연습의 입력 확인은 정답 글자와의 일치만 확인하며, 손글씨 인식이나 애니메이션 획순 기능은 제공하지 않습니다.

### 음성 포함 오프라인 배포판

한 번 AI 음성을 정상적으로 준비한 Windows PC에서 다음 명령을 실행하면, EXE와 준비된 Zundamon API·모델·전용 Python 런타임을 같은 배포 폴더에 넣습니다.

```powershell
.\build_offline_voice_bundle.ps1
```

결과물은 `dist\HaruJapanese-offline\HaruJapanese.exe`와 `zundamon-gpt-sovits-api\` 폴더입니다. 두 항목의 상대 위치를 유지한 채 ZIP으로 묶어 배포하세요. 실행 파일만 따로 옮기면 포함 음성을 찾을 수 없습니다. 완전히 독립적으로 쓰려면 FFmpeg 폴더를 함께 지정합니다.

```powershell
.\build_offline_voice_bundle.ps1 -FfmpegDirectory "C:\tools\ffmpeg\bin"
```

배포 폴더에는 `VOICE-SHA256SUMS.txt`가 생성됩니다. 배포 전에 이 파일로 포함 음성 파일을 점검할 수 있습니다. 수 GB 규모의 음성 파일과 Python 런타임을 포함하므로, 일반 경량판과 별도의 ZIP/설치 프로그램으로 제공하는 것을 권장합니다. 포함 음성 폴더가 불완전하면 앱은 인터넷에서 자동으로 덮어쓰지 않고 배포 폴더를 다시 받도록 안내합니다.

## 개발 이어가기

```powershell
git clone <저장소-주소>
cd myion
python japanese_study.py
```

- Python 3.14와 Tkinter로 만들었습니다.
- 앱 실행에는 별도 Python 패키지가 필요하지 않습니다. EXE 빌드 도구는 `requirements-dev.txt`에 고정 범위로 정의합니다.
- `content.py`는 오프라인 학습 콘텐츠와 획순 안내 데이터를 담습니다.
- `learning_services.py`는 UI와 분리한 학습 설정 검증, 모의고사 시간 요약, CSV 단어장 가져오기 로직을 담습니다.
- `progress_logic.py`는 UI와 분리한 학습 과정 추천, 진단·통계 요약, 정답 피드백 로직을 담습니다.
- `quiz_session.py`는 UI와 분리한 퀴즈 순서, 답안, 오답, 모의고사·진단 점수, 타이머 상태를 관리합니다.
- `ui_quiz.py`는 퀴즈 문제·선택지·청해 제어와 난이도 버튼을 렌더링합니다.
- `ui_screens.py`는 앱 상태와 이벤트를 유지한 채 홈 대시보드, 과정 선택·학습 계획·문자 메뉴, 일일 학습 메뉴, 나의 단어장·즐겨찾기, 복습, 통계 요약·상세·기록 보호 화면 렌더링을 분리합니다.
- `ui_practice.py`는 히라가나·가타카나·한자 쓰기 캔버스, 획순 단계 대화상자, 문장 만들기, 받아쓰기 렌더러를 `japanese_study.py`에서 분리한 모듈입니다.
- `ui_catalog.py`는 단어·한자·문법 카드의 검색, 학습 상태 필터, 즐겨찾기, 메모, 이어 학습, 현재 카드 퀴즈 화면을 렌더링하고 저장과 학습 동작은 앱 콜백으로 유지합니다.
- `ui_dialogs.py`는 화면 크기·색상 대비, 백업·복원, 로컬 AI 음성 설정 대화상자를 렌더링하고 실제 저장·서버 작업은 앱 콜백으로 유지합니다.
- `storage.py`는 SQLite 진도, SRS 일정, 백업·복원, 내보내기와 개인 학습 기록을 관리합니다.
- `tts_service.py`는 로컬 Zundamon GPT-SoVITS의 준비 상태, 도구 확인, 다운로드, 서버 명령을 관리합니다. 모델과 기준 음성 URL은 검토한 upstream revision으로 고정하며, 모든 모델 파일에 예상 SHA-256(`ZUNDAMON_MODEL_FILES` 3-튜플)을 지정해 다운로드 후 검증합니다. 대용량 LFS 파일은 HuggingFace 저장소 메타데이터의 공식 해시를 사용하고, 공식 해시가 없는 작은 파일과 기준 음성은 핀된 revision에서 직접 계산한 해시를 사용합니다.
- `study_logic.py`는 UI와 분리한 학습 안내·계획 페이스·TTS 복구 순수 로직을 담습니다.
- `quiz_logic.py`는 UI와 분리한 문제 풀, 독해·청해 안내, 모의고사 결과 비교 로직을 담습니다.
- `app_info.py`는 앱 버전과 릴리스 정보를 담습니다.
- `japanese_study.py`는 Tkinter 화면과 퀴즈·복습 진행 흐름을 담습니다.
- `build_exe.ps1`은 테스트 후 `dist\HaruJapanese.exe`를 새로 만들고 파일 크기를 확인합니다. 실제 GUI 실행은 Windows 데스크톱에서 별도로 확인하세요.
- `build_installer.ps1`은 Inno Setup 6으로 설치 프로그램을 만들고, 인증서를 지정하면 `signtool`로 서명·검증합니다. `packaging\harujapanese_installer.iss`가 설치 스크립트입니다.
- `gui_smoke_test.py`는 데스크톱 세션에서 모든 주요 화면을 렌더링해 Tcl 오류가 없으면 0, 있으면 0이 아닌 코드로 종료합니다.
- `THIRD_PARTY_NOTICES.md`는 표준 배포판(표준 라이브러리·Tkinter·PyInstaller)과 선택적 음성 배포판(ずんだもん 모델·GPT-SoVITS·FFmpeg·런타임 패키지)의 타사 라이선스 정보를 담습니다.
- `build_offline_voice_bundle.ps1`은 준비된 Zundamon 음성 폴더를 EXE 옆에 복사해, 인터넷 다운로드 없이 실행할 수 있는 대용량 오프라인 배포 폴더와 SHA-256 목록을 만듭니다.
- 개인 학습 기록은 사용자 폴더의 `.haru_japanese\progress.db`에 저장되며 Git에 포함되지 않습니다.

### Windows 릴리스 점검

자동 테스트와 EXE 생성 뒤 Windows 데스크톱에서 `dist\HaruJapanese.exe`를 실행해 홈, 과정 선택, 학습 계획, 문자·카드 학습, 복습, 통계 화면 전환을 확인하세요. 카드 검색·메모·즐겨찾기, 나의 단어장 CSV 가져오기, 백업 묶음 내보내기/가져오기도 테스트용 기록으로 점검하세요. 문자 퀴즈의 선택지·정답 난이도 버튼과 로컬 AI 음성 설정의 연결 확인·테스트 음성을 확인하고, 외부 음성 주소는 경고를 읽은 뒤 신뢰하는 서버에서만 저장하세요. 실제 학습 DB나 모델 다운로드를 공유하지 말고, 필요하면 테스트용 Windows 계정에서 수행하세요.
