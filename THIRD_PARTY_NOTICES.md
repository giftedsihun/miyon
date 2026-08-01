# Third-Party Notices

하루 일본어(Haru Japanese)는 Python 표준 라이브러리와 Tkinter만으로 동작합니다. 실행 환경에 포함되는 타사 구성 요소와, 선택적 로컬 AI 음성(ずんだもん Speech WebUI) 오프라인 배포판에 포함되는 타사 구성 요소의 라이선스 정보를 정리합니다.

이 문서는 저장소에서 참고용으로 제공하는 요약입니다. 배포 시 각 구성 요소의 원본 라이선스 전문을 함께 포함해야 합니다. 아래 표기한 라이선스는 이 문서 작성 시점에 확인된 upstream 정보이며, 배포 전에 실제 포함 파일의 라이선스 전문과 대조해 확인하십시오.

## 1. 기본 실행 파일 (표준 배포판)

| 구성 요소 | 역할 | 라이선스 | 출처 |
| --- | --- | --- | --- |
| Python 표준 라이브러리 | 앱의 전체 런타임 | Python Software Foundation License (PSFL) | https://www.python.org/psf/license/ |
| Tkinter / Tcl / Tk | GUI 프레임워크 (CPython에 포함) | Tcl/Tk License (BSD 계열 허용 라이선스) | https://www.tcl.tk/software/tcltk/license.html |
| PyInstaller | EXE 패키징 (빌드 전용, `requirements-dev.txt`) | GPL-2.0-or-later + 부트로더 예외 | https://pyinstaller.org/ |

> PyInstaller로 만든 실행 파일을 배포할 때는 PyInstaller 라이선스 전문(부트로더 예외 포함)을 배포물에 함께 포함해야 합니다. 기본 배포물에 이 안내와 함께 관련 고지를 포함합니다.

표준 학습 기능(`japanese_study.py`와 동봉 모듈)은 위 구성 요소 외의 타사 런타임 패키지를 사용하지 않습니다. 학습 콘텐츠(`content.py`)는 자체 구성한 교육용 자료이며 공식 JLPT 기출문제나 공식 출제 범위를 재현한 자료가 아닙니다.

## 2. 로컬 AI 음성 (선택적, 오프라인 음성 배포판)

로컬 AI 음성은 첫 실행 시 아래 upstream 자료를 내려받아 `%USERPROFILE%\.haru_japanese\zundamon-gpt-sovits-api\`에 준비합니다. `build_offline_voice_bundle.ps1`로 만든 오프라인 배포판에는 이 구성 요소들이 실행 파일 옆 `zundamon-gpt-sovits-api\` 폴더로 함께 배포됩니다.

### 2.1 음성 및 모델

| 구성 요소 | 역할 | 라이선스 | 출처 |
| --- | --- | --- | --- |
| ずんだもん(Zundamon) 음성 모델 및 기준 음성 | AI 음성 목소리 | SSS LLC. 음원 이용 규약 (https://zunko.jp/con_ongen_kiyaku.html) | https://zunzunpj/zundamon_GPT-SoVITS (Hugging Face) |
| zundamon-speech-webui | ずんだもん 음성용으로 조정된 GPT-SoVITS 기반 WebUI | README에 포함된 구성 요소 라이선스 참고 (GPT-SoVITS MIT, G2PW Apache-2.0, UVR5 MIT, Faster Whisper MIT 등) | https://github.com/zunzun999/zundamon-speech-webui |
| zunzun999/GPT-SoVITS (고정 리비전 `d005f400`) | 음성 추론 API | MIT License (RVC-Boss/GPT-SoVITS의 포크) | https://github.com/zunzun999/GPT-SoVITS |
| lj1995/GPT-SoVITS 사전학습 모델 (chinese-hubert-base, chinese-roberta-wwm-ext-large) | 추론용 사전학습 모델 | MIT License | https://huggingface.co/lj1995/GPT-SoVITS |

> ずんだも노의 캐릭터·음성 사용 규약은 SSS LLC.의 이용 조건에 따릅니다. 배포·상업 이용 전에 https://zunko.jp/con_ongen_kiyaku.html 에서 현재 규약을 반드시 확인하십시오. ずんだもん(ずんだもん)은 SSS LLC.의 상표입니다.

### 2.2 전용 Python 런타임 설치 패키지

오프라인 배포판의 `.haru-runtime` 환경에는 아래 패키지가 설치되어 함께 배포됩니다. 각 패키지의 라이선스 전문은 설치된 `Lib\site-packages\<패키지>.dist-info` 폴더에 포함되며, 배포 시 해당 전문을 보존해야 합니다. 다음 목록은 주요 구성 요소와 일반적으로 알려진 라이선스입니다(배포 전 실제 포함 버전과 대조하십시오).

| 패키지 | 라이선스 |
| --- | --- |
| PyTorch (torch, torchaudio 등) | BSD-3-Clause |
| transformers | Apache-2.0 |
| numpy, scipy, pandas, psutil, soundfile, uvicorn, starlette | BSD-3-Clause |
| numba | BSD-2-Clause |
| librosa | ISC |
| tensorboard, pytorch-lightning, gradio, sentencepiece, modelscope, LangSegment, pyarrow, huggingface_hub | Apache-2.0 |
| tqdm | MIT / MPL-2.0 (이중) |
| ffmpeg-python, pypinyin, pyopenjtalk, PyYAML, jieba, fastapi, typeguard, einops, inflect, g2p_en, cn2an, ko_pron, g2pk2, ToJyutping, wordsegment, rotary_embedding_torch, pydantic | MIT |
| regex | Python Software Foundation License |
| chardet | LGPL-2.1-or-later |
| soxr | LGPL-2.1-or-later |
| matplotlib | Matplotlib License (BSD 계열) |

### 2.3 기타

| 구성 요소 | 역할 | 라이선스 | 출처 |
| --- | --- | --- | --- |
| FFmpeg (선택, 시스템 설치 또는 번들) | 오디오 처리 | LGPL-2.1-or-later (빌드 구성에 따라 GPL 구성 요소 포함 가능) | https://ffmpeg.org/legal.html |

## 3. 배포 시 확인 사항

- 표준 배포판(`dist\HaruJapanese.exe`): PyInstaller 라이선스 전문과 이 문서를 함께 제공합니다.
- 오프라인 음성 배포판(`dist\HaruJapanese-offline\`): 위 2절의 각 upstream 라이선스 전문과 ずんだもん 음원 이용 규약 링크, 그리고 `.haru-runtime`에 설치된 패키지의 `dist-info` 라이선스 파일을 함께 포함합니다.
- 오프라인 음성 배포판을 만들기 전 `VOICE-SHA256SUMS.txt`로 포함 파일을 검증하고, 구성 요소 버전이 바뀌면 이 문서를 갱신하십시오.
- 공식 출처가 확인되지 않은 대용량 모델 파일의 SHA-256은 임의로 등록하지 않습니다. 검증된 해시가 공개되면 `tts_service.py`의 다운로드 항목에 반영합니다.
