# cluster-voice-synthesis-mcp
指定されたテキストを音声合成APIに送信して 音声ファイルを取得して指定オーディオから再生する MCP(Model Context Protocol)サーバー

## 仮装オーディオ
オーディオ一覧の確認機能のために仮装オーディオをインストールします。

```
brew install blackhole-2ch
```

## 仮想環境の作成と有効化

```
cd server/

# 1. 仮想環境を作成（フォルダ名は 'venv' が一般的です）
python3 -m venv venv

# 2. 仮想環境を有効化（アクティベート）
source venv/bin/activate

# (プロンプトの左側に (venv) と表示されれば成功です)
```

## 依存関係のインストール

```
pip install -r requirements.txt
```

## MCPサーバーの設定

設置場所の `venv/bin/python` のフルパスを指定してください。
また、環境変数 `VOICEVOX_API_KEY` に、利用するVOICEVOXサーバーのAPIキーを設定してください。

**必須環境:**
[podman-voicevox-api](https://github.com/tfuru/podman-voicevox-api) を使用したVOICEVOXサーバーが起動していること。

```json
{
  "mcpServers": {
    "cluster-voice-synthesis-mcp": {
      "command": "[pwd]/server/venv/bin/python",
      "args": [
        "[pwd]/server/main.py"
      ],
      "env": {
        "VOICEVOX_URL": "http://127.0.0.1:8080",
        "VOICEVOX_API_KEY": "your_generated_api_key_here"
      }
    }
  }
}
```
* `VOICEVOX_URL`: デフォルトは `http://127.0.0.1:8080`
* `VOICEVOX_API_KEY`: サーバーで発行したAPIキーを指定してください

## 利用可能なツール

このMCPサーバーは以下のツールを提供します。

### `list_output_devices`
現在利用可能なオーディオ出力デバイス（スピーカー、仮想オーディオなど）の一覧を取得します。

### `get_speakers`
VOICEVOXで利用可能な話者（キャラクター）とスタイルの一覧を取得します。

### `set_default_settings`
音声合成のデフォルト設定（話者ID、再生デバイスID）を保存します。
ここで設定した値は、`speak` ツールの引数が省略された場合に使用されます。設定は `server/config.json` に保存されます。

- `speaker_id`: デフォルトの話者ID
- `device_id`: デフォルトの再生デバイスID

### `speak`
テキストを音声合成し、指定されたデバイスで再生します。

- `text`: 読み上げるテキスト内容
- `speaker_id`: 話者ID (省略時は保存された設定を使用。設定もない場合は 1:ずんだもんあまあま)
- `device_id`: 再生するデバイスID (省略時は保存された設定を使用。設定もない場合はシステムの既定デバイス)
