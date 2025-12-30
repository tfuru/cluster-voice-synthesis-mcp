from mcp.server.fastmcp import FastMCP
import httpx
import os
import datetime
import json
import sounddevice as sd
import soundfile as sf

# サーバーの定義
mcp = FastMCP("ClusterVoiceSynthesisMcp")

import tempfile

# VOICEVOXのエンドポイント設定
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:8080")
VOICEVOX_API_KEY = os.environ.get("VOICEVOX_API_KEY", "your_generated_api_key_here")

OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "cluster_voice_synthesis_output")

# 出力フォルダがなければ作成
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

@mcp.tool()
def set_default_settings(speaker_id: int = None, device_id: int = None) -> str:
    """
    音声合成のデフォルト設定（話者ID、再生デバイスID）を保存します。
    指定しなかった項目は変更されません。
    
    Args:
        speaker_id: デフォルトの話者ID
        device_id: デフォルトの再生デバイスID
    """
    config = load_config()
    messages = []
    
    if speaker_id is not None:
        config["default_speaker_id"] = speaker_id
        messages.append(f"話者IDを {speaker_id} に設定しました")
        
    if device_id is not None:
        config["default_device_id"] = device_id
        messages.append(f"デバイスIDを {device_id} に設定しました")
    
    if not messages:
        return "変更する設定が指定されていません (speaker_id または device_id を指定してください)"
        
    save_config(config)
    return "、".join(messages)

@mcp.tool()
def list_output_devices() -> str:
    """
    現在利用可能なオーディオ出力デバイス（スピーカー、オーディオIFなど）の一覧を取得します。
    デバイスIDと名前のリストを返します。再生時にこのデバイスIDを指定してください。
    """
    devices = sd.query_devices()
    output_devices = []
    
    for i, device in enumerate(devices):
        # 出力チャンネルが1以上あるものを出力デバイスとみなす
        if device['max_output_channels'] > 0:
            output_devices.append(f"ID: {i}, Name: {device['name']}")
    
    if not output_devices:
        return "利用可能な出力デバイスが見つかりませんでした。"
        

    return "\n".join(output_devices)

@mcp.tool()
async def get_speakers() -> str:
    """
    VOICEVOXで利用可能な話者（キャラクター）の一覧を取得します。
    """
    headers = {"X-API-KEY": VOICEVOX_API_KEY}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{VOICEVOX_URL}/api/speakers", headers=headers)
            response.raise_for_status()
            speakers = response.json()
            
            result = []
            for speaker in speakers:
                name = speaker["name"]
                styles = []
                for style in speaker["styles"]:
                    styles.append(f"{style['name']}(ID:{style['id']})")
                
                style_str = ", ".join(styles)
                result.append(f"■ {name}\n   {style_str}")
            
            return "\n".join(result)
            
        except httpx.ConnectError:
            return f"エラー: VOICEVOX({VOICEVOX_URL})に接続できませんでした。"
        except httpx.HTTPStatusError as e:
             return f"APIエラー: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def speak(text: str, speaker_id: int = None, device_id: int = None) -> str:
    """
    VOICEVOXを使ってテキストを音声合成し、指定されたデバイスで再生します。
    
    Args:
        text: 読み上げるテキスト内容
        speaker_id: 話者ID。指定しない場合は保存されたデフォルト値、または1(ずんだもんあまあま)が使用されます。
        device_id: 再生するオーディオデバイスID。指定しない場合は保存されたデフォルト値、またはシステムの既定デバイスが使用されます。
    """
    config = load_config()
    
    # デフォルト値の解決
    if speaker_id is None:
        speaker_id = config.get("default_speaker_id", 1)
        
    if device_id is None:
        device_id = config.get("default_device_id") # Noneならデフォルトデバイス
    
    headers = {
        "X-API-KEY": VOICEVOX_API_KEY,
        "Content-Type": "application/json"
    }
    
    timeout = httpx.Timeout(30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            # 1. Synthesis (ワンショットAPI)
            synth_res = await client.post(
                f"{VOICEVOX_URL}/api/synthesis",
                headers=headers,
                json={
                    "text": text,
                    "speaker": speaker_id,
                    "format": "wav"
                }
            )
            synth_res.raise_for_status()

            # 2. ファイルへの保存
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"voice_{timestamp}.wav"
            filepath = os.path.join(OUTPUT_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(synth_res.content)
            
            abs_path = os.path.abspath(filepath)

            # 3. 指定デバイスでの再生
            try:
                # ファイルからデータを読み込む (numpy arrayとサンプリングレートが返る)
                data, fs = sf.read(filepath)
                
                # デバイス指定がある場合はそのIDを使用、なければNone(デフォルト)
                sd.play(data, fs, device=device_id)
                
                # 再生完了待ち
                sd.wait()
                
                device_msg = f"デバイスID {device_id}" if device_id is not None else "デフォルトデバイス"
                status_msg = f"{device_msg}で再生完了"
                
            except Exception as play_error:
                status_msg = f"再生失敗({str(play_error)})"

            return f"音声合成と{status_msg}。保存先: {abs_path}"

        except httpx.ConnectError:
            return f"エラー: VOICEVOX({VOICEVOX_URL})に接続できませんでした。"
        except httpx.HTTPStatusError as e:
             return f"APIエラー: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

if __name__ == "__main__":
    mcp.run()