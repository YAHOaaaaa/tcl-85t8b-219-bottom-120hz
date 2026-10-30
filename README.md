# TCL 85T8B：21:9＋画面位置「下」で 3840x1600@120Hz を出す

TCL 85T8B（日本向け、Google TV）で、純正の Game Bar「画面比率 21:9」「画面位置：下」を有効にしたまま、
PC（RTX 3070）から **3840x1600 / 120Hz** で表示できるようにした調査記録とスクリプトです。

> [!CAUTION]
> **免責事項（必ずお読みください）**
>
> この記録とスクリプトは、個人が自分の機器で試した結果をそのまま置いているだけのものです。メーカー（TCL、NVIDIA、Microsoft ほか）とは一切関係がなく、メーカーが認めた方法でもありません。
> EDID の上書き、グラフィックドライバーの再起動、カスタム解像度、TV のデバッグ機能の利用などを含み、**機器の故障、表示不能、データの消失、保証の対象外になること、その他あらゆる損害が起きる可能性があります。**
> **使う場合はすべて自己責任です。何が起きても作者は一切責任を負いません。故障や不具合が起きても、作者に文句・苦情・損害賠償の請求をしないでください。** これに同意できない場合は使わないでください。
>
> **Disclaimer:** Provided "AS IS", without warranty of any kind. Not affiliated with or endorsed by TCL, NVIDIA or Microsoft. Following these steps may damage your hardware, make your display unusable, void your warranty, or cause other loss. **You use everything here entirely at your own risk; the author accepts no liability whatsoever and you agree not to make any claim or complaint against the author.** Details: [DISCLAIMER.md](DISCLAIMER.md)

## 結果

| 条件 | 結果 | 根拠 |
|---|---|---|
| HDMI 入力 120Hz | ✅ | TV の HDMI 受信部：3840x1600・119.98Hz、FRL 8Gbps×4、DE Stable |
| 純正 21:9＋下 | ✅ | `wideScreenRatio is 1`、`wideScreenPosition is 257`、表示窓 `disp[0,514,3840,1645]`、Game Bar 表示「21:9 / 下」 |
| 表示 | ✅ | Game Bar FPS 120.0、パネル出力 `output_frame_rate` = 120001 |

3回再現（カスタム解像度の試行、保存時、通常のモード切替後）。

## 追記（2026-10-30）：3840x1600@144 も出る

同じ「21:9・下」のまま、**3840x1600@144（CVT-RB、987.26MHz）** も表示できた。ただし **EDID 上書き（Max FRL 8G×4）が必要**。
上書きなしの手順（ハイフレームレートモード OFF → ドライバー再起動 → CVT-RB の 144Hz を作成）は、この TV・ケーブル・端子では再現しなかった。

| 条件 | EDID 上書き | FRL | HDMI 受信 | パネル出力 | 結果 |
|---|---|---|---|---|---|
| 144Hz・CVT-RB | なし（TV の EDID、Max FRL 12G×4） | FRL 12G×4 | DE Stable=0（無信号） | – | 失敗 |
| 144Hz・CVT-RB | 8G×4 | FRL 8G×4 | 3840x1600・143.961Hz・Stable | 144000〜144002 | **成功** |
| 120Hz（比較） | 8G×4 | FRL 8G×4 | 3840x1600・120Hz・Stable | 120000〜120002 | 成功 |

- 条件：Game Bar 21:9・下、**ハイフレームレートモード OFF**、HDMI 互換性設定「自動」、出力 RGB 8bit。
- Game Bar の表示は「FPS 144.0」、表示窓 `disp[0, 514, 3840, 1645]` のまま。
- 7 回再現：試行 30 秒・120 秒・120 秒、保存時、通常のモード変更で 120⇔144 を 3 往復（切替 1 秒後に受信 143.961Hz、3 秒後にパネル 144002）。
- 120 秒間・約 560 回（0.2 秒間隔）の受信部監視で、DE Stable の落ち込みは 0 回。
- 保存直後に 1 回だけ TV がスタンバイに入った（TV は再起動していない。原因は未特定。その後は再発なし）。
- 帯域：987.26MHz × 24bit ≈ 23.7Gbps。FRL 8G×4 の実効（約 27.8Gbps）に収まる。TMDS（600MHz）と 6G×4（約 21.3Gbps）では不足。
- CVT-RB2 は試していない（CVT-RB で成功し、上書きなしの失敗はリンク速度 12G が原因のため）。

```powershell
py -I .\scripts\windows\nvcustom.py 3840 1600 144 30 rb          # 30秒だけ試して自動で戻す
py -I .\scripts\windows\nvcustom.py 3840 1600 144 10 rb --save   # 保存（120Hz とは別のモードとして追加）
.\scripts\windows\rxinfo.ps1                                     # Refresh≈143961, FRL_8G_4CH, DE Stable=1
```

上書きなしの比較には、管理者 PowerShell で `.\scripts\windows\edid_tempremove_admin.ps1` を使った
（上書きを外して GPU ドライバーを再起動し、`edid_tempremove_done.flag` か 300 秒で 8G の上書きを必ず書き戻す）。
詳細は [docs/experiments.md](docs/experiments.md) の T26〜T33。

## 何が 60Hz にしていたか

1. **Game Bar で 21:9 を選ぶと、TV は EDID を差し替える。** 差し替え後の 21:9 用タイミングは
   2560x1080@60 と 3840x1600@59.96 だけ（`libtos_hdmi_service.so` の "Default Wide Screen EDID"）。
   そのため PC は自動で 3840x1600@59 を選ぶ。ハイフレームレートモードを ON にしても、この 2 つは変わらない。
2. **画面位置「下」そのものは原因ではない。** 位置変更は映像ウィンドウを移すだけ
   （`Display_SetWinRegion ... disp[0, 514, 3840, 1645]`）で、EDID も入力信号も変わらない。
3. **3840x1600@120 をカスタム解像度で送ると、NVIDIA ドライバーは FRL 12Gbps×4 を選び、映像が復号されない**
   （受信部 DE Stable=0）。標準の 4K120 は FRL 8Gbps×4 で正常に映る。12G が必要な 4K144 も無信号だった。
   → この環境（ケーブル／端子）では 12Gbps/レーンが通らず、8Gbps/レーンは通る。
4. TMDS（最大 600MHz）では、3840x1600 は CVT-RB2 でも約 90Hz（588MHz）が上限。90Hz は 21:9＋下で動作確認済み。

## 解決方法

**PC 側で EDID を上書きし、TV が申告する最大 FRL レートを 12G×4 → 8G×4 に下げる**
（HF-VSDB の Max_FRL_Rate を 6→4、1 バイトだけ変更）。その上で 3840x1600@120（CVT-RB、813.12MHz）を
NVIDIA カスタム解像度として送る。必要帯域は約 22Gbps なので 8G×4（32Gbps）に収まる。

※ Ultra High Speed HDMI 認証ケーブルで 12G が通るなら、EDID 上書きなしで通る可能性がある（未検証）。

## 再現手順（Windows + adb）

前提：TV で開発者向けオプション＋ネットワークデバッグを有効化、PC から `adb connect <TVのIP>:5555`。
スクリプトは TV の adb シリアルを自動検出します（複数ある場合は `$env:TV_SERIAL` を設定）。

1. TV：Game Bar → メニュー → 画面比率 **21:9**、画面位置 **下**。ハイフレームレートモードは **OFF**、
   HDMI 互換性設定は **自動**。
2. PC：EDID 上書きを作る（TV が 21:9 モードの状態で実行）
   ```powershell
   .\scripts\windows\edid_make.ps1
   ```
3. PC：管理者 PowerShell で上書きを適用（GPU ドライバーを再起動。180 秒以内に `edid_keep.flag` を作らないと自動で元に戻る）
   ```powershell
   .\scripts\windows\edid_apply_admin.ps1 -Timeout 180
   ```
   表示が正常なら `scripts\windows\edid_keep.flag` を作成して維持する。
4. PC：3840x1600@120 を試行 → 問題なければ保存
   ```powershell
   py -I .\scripts\windows\nvcustom.py 3840 1600 120 30          # 30秒だけ試して自動で戻す
   py -I .\scripts\windows\nvcustom.py 3840 1600 120 6 rb --save # 保存
   .\scripts\windows\setmode.ps1 -W 3840 -H 1600 -Hz 120 -Keep -Persist
   ```
5. 確認
   ```powershell
   .\scripts\windows\rxinfo.ps1            # FRL Rate=FRL_8G_4CH, Width=3840, Height=1600, Refresh≈120000, DE Stable=1
   adb -s <TV> logcat -d | findstr "SetWinRegion getWideScreenPosition"   # disp[0, 514, 3840, 1645] / 257
   Get-Content .\scripts\tv\panel_read.sh -Raw | adb -s <TV> shell sh   # output_frame_rate ≈ 120000
   ```

## 元に戻す

1. 管理者 PowerShell：`.\scripts\windows\edid_apply_admin.ps1 -Remove`（上書き削除＋GPU ドライバー再起動）
2. NVIDIA コントロールパネル → 解像度の変更 → カスタマイズ で 3840x1600@120 を削除
3. TV：Game Bar で 16:9・中間

## 注意

- EDID 上書き中は、PC は TV 側の EDID 変更（16:9 / 21:9 / ハイフレームレート）を見ない。
- GPU ドライバー再起動後、Windows のディスプレイ名（`\\.\DISPLAYn`）が変わることがある。スクリプトはプライマリを自動検出する。
- PC の再起動後も、EDID 上書きとカスタム解像度は維持された（2026-10-30 確認）。TV の再起動後は未確認。
- ハイフレームレートモードを ON/OFF すると、TV が HDMI 互換性設定を「オン」に書き換えることがあった。戻すときは「自動」に。
- `output_frame_rate`（MediaTek デバッグノード）の意味は数値の挙動からの推定（60Hz 入力時は 119926＝入力の 2 倍）。
- **YCbCr 4:2:0 にはできない**（カスタムタイミングには 4:2:0 が使われない）。詳細は [docs/findings.md](docs/findings.md)。
- 瞬断（一瞬のブラックアウト）が出る場合は、NVIDIA の出力色を RGB・フルレンジにすると止まった例がある（関連は未確定）。
  回数は `scripts/windows/dropcount.ps1` で数えられる。

## 中身

| パス | 内容 |
|---|---|
| `scripts/windows/nvcustom.py` | NVAPI `TryCustomDisplay`／`SaveCustomDisplay` でカスタム解像度（CVT-RB／RB2）を試行・保存 |
| `scripts/windows/edid_make.ps1` | 現在の EDID から Max_FRL_Rate を下げた上書き用 EDID を生成 |
| `scripts/windows/edid_apply_admin.ps1` | EDID 上書きの適用／削除（自動ロールバック付き、要管理者） |
| `scripts/windows/edid_tempremove_admin.ps1` | EDID 上書きを一時的に外し、合図か時間切れで 8G の上書きを必ず書き戻す（比較試験用、要管理者） |
| `scripts/windows/rxinfo.ps1` | TV の HDMI 受信部状態（FRL レート、タイミング、色形式）を表示 |
| `scripts/windows/setmode.ps1` / `listmodes.ps1` | Windows の表示モード変更（自動復帰付き）／一覧 |
| `scripts/windows/parse_edid.ps1` | Windows が保存した EDID のデコード |
| `scripts/windows/nvcolor.py` / `nvcolor_probe.py` / `nvcolor_restore.py` | NVAPI 色形式の取得・変更・対応確認・RGB への復帰 |
| `scripts/windows/dropcount.ps1` | 一定時間内の TV 受信部の瞬断回数を数える |
| `scripts/windows/ui.ps1` | uiautomator で TV の UI を読み、キー操作（Game Bar の操作に使用） |
| `scripts/tv/*.sh` | TV 上で読む sysfs（パネル出力レート、HDMI 受信部デバッグ） |
| `scripts/analysis/dexscan.py` / `dexflow.py` | 依存なしの簡易 DEX/ELF 文字列・呼び出し列挙（APK 解析用） |
| `docs/findings.md` | 解析の詳細（Game Bar／TV サービスの内部、EDID、HDMI 受信部） |
| `docs/experiments.md` | 試験の記録（T1〜T25） |

APK・ネイティブライブラリ・生ログ・生 EDID は含めていません（著作権と個人情報のため）。
