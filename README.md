# トレイン発車

神戸新交通ポートアイランド線の保存済み時刻表を使って、各駅の先発・次発・次々発を表示するアプリです。  
Python / Tkinter のデスクトップ版と、Google Sites へ埋め込み可能な静的 Web 版を用意しています。

## できること

- 駅名を選択して発車案内を表示
- 方面を選択して先発・次発・次々発を表示
- 公式サイトから時刻表を取得して保存
- 保存済み時刻表があれば、通常利用時はそのデータを利用
- `PyInstaller` による実行ファイル化に対応
- `GitHub Pages` で公開できる静的 Web アプリを生成可能
- `config/app_settings.json` でデフォルトの駅・方面を設定可能

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

## デフォルト表示の設定

起動時の駅名と方面は [config/app_settings.json](/Users/ohtsuka/workspace/train-hassha/config/app_settings.json) で変更できます。

```json
{
  "default_station_name": "三宮",
  "default_direction_name": "神戸空港・北埠頭方面行"
}
```

この設定はデスクトップ版の初期表示と、Web 版の公開ページの初期表示の両方に使われます。

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

## Web 版の生成

保存済み時刻表から静的 Web サイトを書き出します。

```bash
.venv/bin/python build_web_site.py
```

時刻表も再取得してから書き出す場合:

```bash
.venv/bin/python build_web_site.py --refresh-data
```

出力先は `site/` です。

## GitHub Pages 公開

このリポジトリには [`.github/workflows/deploy-pages.yml`](/Users/ohtsuka/workspace/train-hassha/.github/workflows/deploy-pages.yml) を追加してあります。`main` ブランチへ push すると GitHub Actions が次を行います。

1. 公式サイトから時刻表を取得
2. 公開用の静的 Web サイトを生成
3. GitHub Pages へデプロイ

公開 URL は通常、以下の形になります。

```text
https://bekuta-jp.github.io/train_hassha/
```

Google Sites にはこの URL を「埋め込み」または「フルページ埋め込み」で追加してください。

初期表示を URL で上書きしたい場合は、次のようにクエリパラメータを使えます。

```text
https://bekuta-jp.github.io/train_hassha/?station=三宮&direction=神戸空港・北埠頭方面行
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
- Web 版は `Asia/Tokyo` を基準に現在時刻とダイヤを判定します。
- Codex などのサンドボックス内では macOS の `Tkinter` 初期化で落ちることがあるため、その場合は Terminal / Finder から起動してください。
