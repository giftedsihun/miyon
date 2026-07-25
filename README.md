# 하루 일본어

완전 초보부터 JLPT N1 수준까지 이어지는 오프라인 Windows 일본어 학습 앱입니다.

> 이 저장소의 학습 자료는 자체 구성한 교육용 자료입니다. 공식 JLPT 기출문제나
> 공식 출제 범위를 그대로 재현하지 않습니다.

포함 기능:

- 히라가나·가타카나 기본 46자, 탁음·반탁음·요음, 촉음·장음 규칙 학습
- N5~N1 수준별 자체 구성 단어, 한자, 문법 카드와 예문
- 직접 과정 선택 또는 12문항 균형 진단으로 시작 단계 추천
- 단어·한자·문법·문자 혼합 퀴즈, 자동 오답 기록, 오늘의 복습
- 단계별 짧은 독해, 대본 숨김·느린 속도 반복 재생 청해 연습, 12문항 종합 모의고사
- 로컬 ずんだもん Speech WebUI AI 음성으로 예문과 청해 대화 재생
- 히라가나·가타카나 입력 확인 쓰기 연습, 한자 참고 획순 안내, 마우스·터치 필기 칸과 획 수 기록
- 1·2·4·7·14·30·60일 간격 복습과 일일 학습, 연속 학습, 정답률 통계
- 영역별 시험 기록과 누적 정답률
- SQLite 기반 완전 오프라인 학습 기록 저장

## 실행

```powershell
python japanese_study.py
```

## EXE 만들기

PowerShell에서 실행합니다.

```powershell
.\build_exe.ps1
```

완성된 파일은 `dist\HaruJapanese.exe`에 생성됩니다.

학습 진도는 사용자 폴더의 `.haru_japanese\progress.db`에 저장되므로 프로그램을 다시 실행해도 단계 선택, 퀴즈 결과, 오답 노트가 유지됩니다.

학습 자료는 `content.py`에 포함되어 있습니다. 이 앱의 자료는 오프라인 학습을 위해 자체 구성한 과정이며, 공식 JLPT 기출문제나 공식 출제 범위를 그대로 재현한 자료는 아닙니다.

## 로컬 AI 음성 (ずんだもん Speech WebUI)

AI 음성은 [zunzun999/zundamon-speech-webui](https://github.com/zunzun999/zundamon-speech-webui)의 ずんだもん GPT-SoVITS 모델을 사용합니다. 모델 서버는 내 PC에서만 실행하며 외부 클라우드 API나 API 키를 사용하지 않습니다.

1. 앱을 열거나 `발음 듣기`를 누르면 하루 일본어가 AI 서버 상태를 확인합니다. 서버가 꺼져 있으면 사용자 폴더의 `.haru_japanese\zundamon-speech-webui`에 프로젝트를 내려받고, 전용 Python 3.10 환경과 CPU용 실행 패키지를 준비합니다.
2. 이어서 ずんだもん 파인튜닝 모델과 필요한 GPT-SoVITS 추론 모델을 자동으로 내려받습니다. 첫 실행에는 수 GB의 파일과 패키지를 받아야 하므로 인터넷 속도에 따라 오래 걸릴 수 있습니다. 이때 앱을 닫지 마세요.
3. 준비가 끝나면 앱이 전용 환경으로 로컬 API 서버를 자동 시작합니다. 모든 `발음 듣기`와 청해 재생은 이 하나의 ずんだもん AI 음성만 사용합니다.
4. 홈의 `AI 음성 확인/시작`에서 진행 상태를 다시 확인하거나 시작을 재시도할 수 있습니다. 준비 또는 서버 시작 오류는 `.haru_japanese\zundamon-setup.log` 및 `.haru_japanese\zundamon-api.log`에 저장됩니다.

기본 주소는 `http://127.0.0.1:9880`입니다. 앱은 GPT-SoVITS API의 `POST /` 엔드포인트로 `text`, `text_language: "ja"`, `speed`를 보내 일본어 WAV 오디오를 요청합니다. 외부 클라우드 API나 API 키를 사용하지 않습니다.

이 앱은 Windows 일본어 음성을 사용하지 않습니다. 자동 시작은 기본으로 켜져 있으며, 필요하면 `AI 음성 설정`에서 끌 수 있습니다. 쓰기 연습의 입력 확인은 정답 글자와의 일치만 확인하며, 손글씨 인식이나 애니메이션 획순 기능은 제공하지 않습니다.

## 개발 이어가기

```powershell
git clone <저장소-주소>
cd jpan
python japanese_study.py
```

- Python 3.14와 Tkinter로 만들었습니다.
- `content.py`는 오프라인 학습 콘텐츠와 획순 안내 데이터를 담습니다.
- `japanese_study.py`는 UI, SQLite 진도 저장, 퀴즈, 복습 로직을 담습니다.
- `build_exe.ps1`을 실행하면 `dist\HaruJapanese.exe`를 새로 만듭니다.
- 개인 학습 기록은 사용자 폴더의 `.haru_japanese\progress.db`에 저장되며 Git에 포함되지 않습니다.
