"""Local Zundamon GPT-SoVITS setup and transport helpers.

Tkinter scheduling, dialogs, and saved user preferences remain in the UI layer.
"""

import base64
import hashlib
import json
import shutil

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from storage import DATA_DIR


def bundled_voice_directory(executable_path=None, frozen=None):
    """Return an adjacent voice directory only for a frozen portable release."""
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if not frozen:
        return None
    executable = Path(executable_path or sys.executable).resolve()
    candidate = executable.parent / "zundamon-gpt-sovits-api"
    return candidate if candidate.is_dir() else None


def bundled_voice_status(directory=None):
    """Describe whether an adjacent release folder contains the minimum voice runtime."""
    directory = Path(directory) if directory else BUNDLED_ZUNDAMON_DIRECTORY
    if directory is None:
        return False, ""
    required = (
        directory / "api.py",
        directory / ".haru-runtime" / "Scripts" / "python.exe",
        directory / "reference" / "reference.wav",
        directory / "GPT_weights_v2" / "zudamon_style_1-e15.ckpt",
        directory / "SoVITS_weights_v2" / "zudamon_style_1_e8_s96.pth",
    )
    missing = [str(path.relative_to(directory)) for path in required if not file_ready(path)]
    return not missing, ", ".join(missing)


ZUNDAMON_URL = "http://127.0.0.1:9880"
ZUNDAMON_REPOSITORY = "https://github.com/zunzun999/GPT-SoVITS.git"
ZUNDAMON_REVISION = "d005f4005512a9a4bd592f06f206601e420f8582"
BUNDLED_ZUNDAMON_DIRECTORY = bundled_voice_directory()
ZUNDAMON_DIRECTORY = BUNDLED_ZUNDAMON_DIRECTORY or DATA_DIR / "zundamon-gpt-sovits-api"
ZUNDAMON_API_DIRECTORY = ZUNDAMON_DIRECTORY
ZUNDAMON_RUNTIME = ZUNDAMON_DIRECTORY / ".haru-runtime"
ZUNDAMON_GPT_MODEL = ZUNDAMON_API_DIRECTORY / "GPT_weights_v2" / "zudamon_style_1-e15.ckpt"
ZUNDAMON_SOVITS_MODEL = ZUNDAMON_API_DIRECTORY / "SoVITS_weights_v2" / "zudamon_style_1_e8_s96.pth"
ZUNDAMON_REFERENCE_TEXT = "流し切りが完全に入ればデバフの効果が付与される"
ZUNDAMON_SPEECH_WEBUI_REVISION = "cf5104f20781e3e81be499cd0c872b9801be1c51"
ZUNDAMON_MODEL_REVISION = "f780c52eca8701f1ce021e9cef44e44c6be7dbc0"
GPT_SOVITS_MODEL_REVISION = "336b2ec4e8d4ac74740798dd40af44e74659ecaf"
ZUNDAMON_REFERENCE_SOURCE = f"https://raw.githubusercontent.com/zunzun999/zundamon-speech-webui/{ZUNDAMON_SPEECH_WEBUI_REVISION}/reference/reference.wav"
ZUNDAMON_REFERENCE_AUDIO = ZUNDAMON_DIRECTORY / "reference" / "reference.wav"
# 기준 음성은 GitHub raw에 공개 SHA-256이 없어 핀된 리비전 파일을 받아 직접 계산한 값입니다.
ZUNDAMON_REFERENCE_SHA256 = "b41e3f0d539c2c294fdbf03349b8b07127bad9576e52936d45c190c7eec07b02"
ZUNDAMON_SETUP_LOG = DATA_DIR / "zundamon-setup.log"
ZUNDAMON_SERVER_LOG = DATA_DIR / "zundamon-api.log"
ZUNDAMON_READY_MARKER = ZUNDAMON_RUNTIME / ".haru-zundamon-ready"
ZUNDAMON_READY_CONTENT = f"ready {ZUNDAMON_REVISION}\n"
ZUNDAMON_MODEL_FILES = (
    # 각 항목은 (소스 URL, 저장 경로, 예상 SHA-256)입니다. 대용량 LFS 파일은 HuggingFace
    # 저장소 메타데이터의 ETag(=공식 SHA-256)이고, JSON/tokenizer 같은 작은 비-LFS 파일은
    # 공식 해시가 없어 핀된 리비전에서 받아 직접 계산한 값입니다.
    (f"https://huggingface.co/zunzunpj/zundamon_GPT-SoVITS/resolve/{ZUNDAMON_MODEL_REVISION}/GPT_weights_v2/zudamon_style_1-e15.ckpt", ZUNDAMON_GPT_MODEL, "9a655c830c707a3ac9a36a437886928c97894747351511da85b2c94320cece2e"),
    (f"https://huggingface.co/zunzunpj/zundamon_GPT-SoVITS/resolve/{ZUNDAMON_MODEL_REVISION}/SoVITS_weights_v2/zudamon_style_1_e8_s96.pth", ZUNDAMON_SOVITS_MODEL, "de30c810949f1a170aae3f2fa8ab71b3d4e2cad78da508f07be871aef8491da6"),
    (f"https://huggingface.co/lj1995/GPT-SoVITS/resolve/{GPT_SOVITS_MODEL_REVISION}/chinese-hubert-base/config.json", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base" / "config.json", "c3e5060a1277e0f078cc6be9da4528a605dba6ece93018981fe2c820e5c7b103"),
    (f"https://huggingface.co/lj1995/GPT-SoVITS/resolve/{GPT_SOVITS_MODEL_REVISION}/chinese-hubert-base/preprocessor_config.json", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base" / "preprocessor_config.json", "dcd684124d06722947939d41ea6ae58dbf10968c60a11a29f23ddc602c64a29b"),
    (f"https://huggingface.co/lj1995/GPT-SoVITS/resolve/{GPT_SOVITS_MODEL_REVISION}/chinese-hubert-base/pytorch_model.bin", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base" / "pytorch_model.bin", "fb2028f4a31a17a464d12317f7ec7e5c551104da078fb2f6238ee87f460e8e82"),
    (f"https://huggingface.co/lj1995/GPT-SoVITS/resolve/{GPT_SOVITS_MODEL_REVISION}/chinese-roberta-wwm-ext-large/config.json", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large" / "config.json", "3d57de2fd7e80d0e5c8ff194f0bbb6baa10df7e43fc262a0cc71298a78b0a3e5"),
    (f"https://huggingface.co/lj1995/GPT-SoVITS/resolve/{GPT_SOVITS_MODEL_REVISION}/chinese-roberta-wwm-ext-large/pytorch_model.bin", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large" / "pytorch_model.bin", "cc347a6ac57fe7c9830f6be93e68423580acb87bfae382a4b53d9f9703f2cfc3"),
    (f"https://huggingface.co/lj1995/GPT-SoVITS/resolve/{GPT_SOVITS_MODEL_REVISION}/chinese-roberta-wwm-ext-large/tokenizer.json", ZUNDAMON_API_DIRECTORY / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large" / "tokenizer.json", "173796956820ea27bd14f76bf28162607ff4254807e2948253eb5b46f5bb643b"),
)
ZUNDAMON_PYTHON_PACKAGES = (
    "numpy==1.23.4", "scipy", "tensorboard", "librosa==0.9.2", "numba==0.56.4",
    "pytorch-lightning", "gradio>=4.0,<=4.24.0", "ffmpeg-python", "tqdm", "cn2an", "pypinyin",
    "pyopenjtalk>=0.3.4", "g2p_en", "modelscope==1.10.0", "sentencepiece", "transformers==4.39.3",
    "chardet", "PyYAML", "psutil", "jieba", "wordsegment", "rotary_embedding_torch", "ToJyutping",
    # OpenCC is only used by optional Chinese conversion flows and has no Python 3.9 Windows wheel.
    "LangSegment>=0.2.0", "g2pk2", "ko_pron", "fastapi<0.112.2", "uvicorn", "soundfile",
    "onnxruntime", "typeguard", "regex", "gruut", "pandas", "matplotlib", "einops", "inflect", "soxr",
)

# 사전 생성된 즈단몬 음성 캐시: speak_japanese가 실시간 서버 대신 즉시 재생합니다.
# 패키징된 EXE 실행 시에는 EXE 옆의 voice_cache/를, 개발 모드에서는 소스 트리의 voice_cache/를 사용합니다.
def _voice_cache_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "voice_cache"
    return Path(__file__).resolve().parent / "voice_cache"


VOICE_CACHE_DIRECTORY = _voice_cache_directory()


def voice_cache_path(text, speed=1.0):
    """Return the on-disk wav path for a text+speed pair (deterministic hash)."""
    key = hashlib.sha1(f"{text}|{speed:.2f}".encode("utf-8")).hexdigest()
    return VOICE_CACHE_DIRECTORY / f"{key}.wav"


def cached_voice(text, speed=1.0):
    """Return a ready cached wav path, or None if no valid cached audio exists."""
    path = voice_cache_path(text, speed)
    if path.is_file() and path.stat().st_size > 1024:
        return path
    return None


# ttsclient 백엔드 (w-okada/ttsclient REST API 서버)
TTS_CLIENT_DIRECTORY = Path(__file__).resolve().parent / "ttsclient"
TTS_CLIENT_RUNTIME = TTS_CLIENT_DIRECTORY / ".venv" / "Scripts" / "python.exe"
TTS_CLIENT_URL = "http://127.0.0.1:19000"
TTS_CLIENT_SERVER_LOG = TTS_CLIENT_DIRECTORY / "server.log"
# 즈단몬 공식 샘플: voice character slot 4(즈단몬), 그 안의 참조 음성 slot 0
TTS_CLIENT_VOICE_CHARACTER_SLOT_INDEX = 4
TTS_CLIENT_REFERENCE_VOICE_SLOT_INDEX = 0
TTS_CLIENT_MODEL_FILES = (
    # (GPT 모델, SoVITS 모델, 참조 음성 wav) — ttsclient가 샘플로 내장해 둔 즈단몬 모델 파일
    TTS_CLIENT_DIRECTORY / "models" / "3" / "zudamon_style_1-e15.ckpt",
    TTS_CLIENT_DIRECTORY / "models" / "3" / "zudamon_style_1_e8_s96.pth",
    TTS_CLIENT_DIRECTORY / "voice_characters" / "4" / "32883806-20c6-4822-87df-2f30c35bcac7.wav",
)


def ttsclient_ready():
    """Return whether the bundled ttsclient runtime and Zundamon model files exist."""
    gpt_sovits_src = TTS_CLIENT_DIRECTORY / "third_party" / "GPT-SoVITS" / "GPT_SoVITS"
    if not (TTS_CLIENT_RUNTIME.is_file() and gpt_sovits_src.is_dir()):
        return False
    return all(file_ready(path) for path in TTS_CLIENT_MODEL_FILES)


def ttsclient_server_command():
    return [
        str(TTS_CLIENT_RUNTIME), "-m", "ttsclient.main", "cui",
        "--launch_client", "False", "--no_cui", "False",
    ]


def ttsclient_generate_voice(text, speed=1.0):
    """Request WAV bytes from the ttsclient generateVoice endpoint."""
    payload = json.dumps({
        "voice_character_slot_index": TTS_CLIENT_VOICE_CHARACTER_SLOT_INDEX,
        "reference_voice_slot_index": TTS_CLIENT_REFERENCE_VOICE_SLOT_INDEX,
        "text": text,
        "language": "all_ja",
        "speed": speed,
        "cutMethod": "No slice",
    }).encode("utf-8")
    request = urllib.request.Request(
        TTS_CLIENT_URL + "/api/tts-manager/operation/generateVoice",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return response.read()


def api_available(url, timeout=5):
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/docs", timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def is_local_endpoint(url):
    """Accept loopback-only defaults without treating arbitrary URLs as private."""
    value = str(url).strip().lower().split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    return value in {"127.0.0.1", "localhost", "::1"}


def endpoint_privacy_notice(url):
    if is_local_endpoint(url):
        return "로컬 주소입니다. 발음 요청 텍스트는 이 PC의 AI 서버에만 전달됩니다."
    return "외부 주소입니다. 발음 요청의 일본어 텍스트가 해당 서버로 전송될 수 있습니다. 신뢰하는 서버에서만 사용하세요."


def runtime_python():
    return ZUNDAMON_RUNTIME / "Scripts" / "python.exe"


def file_ready(path):
    try:
        # Configuration JSON files are legitimately smaller than model binaries.
        minimum_size = 1 if Path(path).suffix.lower() == ".json" else 1024
        return path.is_file() and path.stat().st_size >= minimum_size
    except OSError:
        return False


def ready():
    required = (ZUNDAMON_API_DIRECTORY / "api.py", runtime_python())
    model_files = (ZUNDAMON_REFERENCE_AUDIO, ZUNDAMON_GPT_MODEL, ZUNDAMON_SOVITS_MODEL) + tuple(destination for _, destination, _ in ZUNDAMON_MODEL_FILES[2:])
    if not all(path.is_file() for path in required) or not all(file_ready(path) for path in model_files):
        return False
    try:
        return ZUNDAMON_READY_MARKER.read_text(encoding="ascii") == ZUNDAMON_READY_CONTENT
    except OSError:
        return False


def installation_summary():
    required = (ZUNDAMON_API_DIRECTORY / "api.py", runtime_python())
    model_files = (ZUNDAMON_REFERENCE_AUDIO, ZUNDAMON_GPT_MODEL, ZUNDAMON_SOVITS_MODEL) + tuple(destination for _, destination, _ in ZUNDAMON_MODEL_FILES[2:])
    return len(required), sum(path.is_file() for path in required), len(model_files), sum(file_ready(path) for path in model_files)


def missing_commands():
    commands = ("git", "uv", "ffmpeg")
    bundled_ffmpeg = ZUNDAMON_DIRECTORY / "tools" / "ffmpeg" / "ffmpeg.exe"
    return [command for command in commands if shutil.which(command) is None and not (command == "ffmpeg" and bundled_ffmpeg.is_file())]


def runtime_environment(environment=None):
    """Expose an optionally bundled FFmpeg only to the local voice server process."""
    result = dict(environment or {})
    bundled_tools = ZUNDAMON_DIRECTORY / "tools" / "ffmpeg"
    if bundled_tools.is_dir():
        result["PATH"] = str(bundled_tools) + ";" + result.get("PATH", "")
    return result



def prerequisite_error():
    missing = missing_commands()
    if not missing:
        return None
    instructions = {"git": "Git", "uv": "uv (https://docs.astral.sh/uv/)", "ffmpeg": "FFmpeg (winget install Gyan.FFmpeg)"}
    return f"AI 음성 준비 전 {', '.join(missing)}이 필요해요. 설치: " + " / ".join(instructions[item] for item in missing)


def server_command():
    return [str(runtime_python()), "api.py", "-d", "cpu", "-fp", "-p", "9880", "-g", str(ZUNDAMON_GPT_MODEL), "-s", str(ZUNDAMON_SOVITS_MODEL), "-dr", "reference\\reference.wav", "-dt", ZUNDAMON_REFERENCE_TEXT, "-dl", "ja"]


def run_command(arguments, log_file, timeout, set_status):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as output:
        output.write("\n$ " + subprocess.list2cmdline([str(value) for value in arguments]) + "\n")
        output.flush()
        result = subprocess.run([str(value) for value in arguments], stdout=output, stderr=subprocess.STDOUT, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        set_status("AI 음성 준비에 실패했어요. 자세한 오류는 " + str(log_file) + "에서 확인해 주세요.", "#b95140")
        return False
    return True


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as input_file:
        for block in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_file(source, destination, expected_sha256=None, attempts=3):
    """Download atomically, retry transient failures, and verify supplied digests."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    attempts = max(1, int(attempts))
    minimum_size = 1 if destination.suffix.lower() == ".json" else 1024
    for attempt in range(attempts):
        temporary.unlink(missing_ok=True)
        try:
            request = urllib.request.Request(source, headers={"User-Agent": "HaruJapanese/1.0"})
            with urllib.request.urlopen(request, timeout=180) as response, open(temporary, "wb") as output:
                shutil.copyfileobj(response, output)
            if temporary.stat().st_size < minimum_size:
                raise OSError("다운로드한 파일이 비어 있거나 너무 작습니다.")
            if expected_sha256 and file_sha256(temporary).lower() != expected_sha256.lower():
                raise OSError("다운로드한 파일의 SHA-256 검증에 실패했습니다.")
            temporary.replace(destination)
            return file_sha256(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt + 1 == attempts:
                raise
            time.sleep(attempt + 1)


def speak_windows_native(text, rate=0):
    """Fallback TTS using Windows built-in SAPI.SpVoice (zero extra downloads or installations)."""
    try:
        sapi_rate = max(-10, min(10, int(rate)))
        clean_text = str(text).replace("'", "''").replace("\n", " ")
        ps_script = (
            f"$v = New-Object -ComObject SAPI.SpVoice; "
            f"$v.Rate = {sapi_rate}; "
            f"foreach ($voice in $v.GetVoices()) {{ "
            f"if ($voice.GetDescription() -like '*Japanese*' -or $voice.GetDescription() -like '*Haruka*' -or $voice.GetDescription() -like '*Ayumi*' -or $voice.GetDescription() -like '*Ichiro*') {{ $v.Voice = $voice; break }} "
            f"}}; "
            f"$v.Speak('{clean_text}')"
        )
        encoded_script = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_script]
        subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except Exception:
        return False


