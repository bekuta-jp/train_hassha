# トレイン発車

神戸新交通ポートアイランド線の保存済み時刻表を使って、各駅の先発・次発・次々発を表示する Python アプリです。  
公式サイトから時刻表をワンボタンで取得して保存し、その保存データをもとに案内を表示します。

## できること

- 駅名を選択して発車案内を表示
- 方面を選択して先発・次発・次々発を表示
- 公式サイトから時刻表を取得して保存
- 保存済み時刻表があれば、通常利用時はそのデータを利用
- `PyInstaller` による実行ファイル化に対応

## 開発環境の準備

### macOS / Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## アプリの起動

### macOS / Linux

```bash
./run_unix.sh
```

### Windows

```bat
run_windows.bat
```

または共通で次のコマンドでも起動できます。

```bash
.venv/bin/python main.py
```

## 使い方

1. アプリを起動します。
2. `時刻表を取得して保存` を押します。
3. 駅名と方面を選ぶと、保存済み時刻表から `先発 / 次発 / 次々発` が表示されます。

保存先は OS ごとのユーザーデータ領域です。

- Windows: `%APPDATA%\TrainHassha`
- macOS: `~/Library/Application Support/TrainHassha`
- Linux: `~/.local/share/train-hassha`

## コマンドライン利用

時刻表を取得して保存:

```bash
.venv/bin/python main.py --fetch-only
```

保存済み時刻表の駅一覧を表示:

```bash
.venv/bin/python main.py --list-stations
```

指定駅の方面一覧を表示:

```bash
.venv/bin/python main.py --list-directions 三宮
```

指定駅・方面の次の列車を表示:

```bash
.venv/bin/python main.py --station 三宮 --direction 神戸空港・北埠頭方面行
```

デバッグ用に基準時刻を指定して表示:

```bash
.venv/bin/python main.py --station 三宮 --direction 神戸空港・北埠頭方面行 --now "2026-04-17 23:59"
```

## 実行ファイル化

### macOS / Linux

```bash
./build_unix.sh
```

### Windows

```bat
build_windows.bat
```

出力先は `dist/` です。

## 補足

- macOS では `PyInstaller` の都合に合わせて `onedir` 形式で出力します。
- Windows 用 `.exe` は Windows 環境で `PyInstaller` を実行して作成してください。
- 時刻表の判定は保存済みデータを使います。再取得しない限り、表示内容は保存時点のままです。
- 終電後は翌日の日付で曜日・祝日を再判定して、翌日のダイヤを表示します。
- Codex などのサンドボックス内では macOS の `Tkinter` 初期化で落ちることがあるため、その場合は Terminal / Finder から起動してください。
