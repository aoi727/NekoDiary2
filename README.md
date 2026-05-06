# NekoDiary

PySide6 で作成した日記アプリです。SQLite データベースを使って日記の作成、編集、検索、カテゴリ管理を行えます。

## 動作環境

- Python 3.9 以上
- PySide6

## プロジェクト内で完結するファイル配置

実行時に使う設定は、起動時に読めるアプリの場所へ保存します。日記本文へ挿入した画像は、選択した SQLite DB ファイルと同じフォルダへ保存します。

- `settings.ini`: 最後に使った DB パスやウィンドウ位置。開発時はプロジェクト直下、Windows 実行ファイルでは `NekoDiary.exe` と同じフォルダ
- `<DBファイルと同じフォルダ>/img/`: 日記本文へ挿入した画像
- `Sozai/`: UI アイコン素材
- SQLite DB: 初回起動時に選択または新規作成

日記データをまとめて移動したい場合は、SQLite DB と `img/` を同じフォルダに置いたまま移動してください。移動後は初回起動時に移動先の DB を選び直します。

## セットアップ

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

または、次のスクリプトでローカル仮想環境の作成から起動まで行えます。

```powershell
.\run.ps1
```

## 起動方法

```powershell
.\.venv\Scripts\python.exe -m src.main
```

初回起動時、または保存済みのデータベースパスが見つからない場合は、使用する SQLite データベースファイルを選択または新規作成します。

## Windows 実行ファイルの作成

```powershell
.\build_windows.ps1
```

生成物は `dist/NekoDiary/NekoDiary.exe` に出力されます。`Sozai/` と `src/style.qss` は実行ファイル側へ同梱されます。

## バックアップ

ツールバーの保存ボタンから、使用中の SQLite DB と DB 横の `img/` フォルダをひとつの ZIP ファイルとして保存できます。ZIP 形式は Python 標準機能で作成しているため、Windows 専用ではありません。

## 主な構成

- `src/`: アプリ本体
- `Sozai/`: UI 用画像
- `img/`: 日記本文へ挿入した画像の保存先。DB ファイルと同じフォルダに自動作成
- `仕様書.md`: 仕様メモ
