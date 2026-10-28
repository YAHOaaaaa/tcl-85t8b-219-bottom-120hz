# 解析の詳細

免責事項は [../DISCLAIMER.md](../DISCLAIMER.md) を参照。

## 対象

| 項目 | 値 |
|---|---|
| TV | TCL 85T8B（日本向け）。`ro.product.clientType=TCL-JP-MT9653-S1`、`ro.product.model=Smart TV Pro` |
| SoC | MediaTek（`ro.hardware=mt5896`、`ro.hardware.version_id=MT9653_Overseas`） |
| ソフトウェア | `V8-T653T01-LF1V228`、Android 12（SDK 31） |
| Game Bar | `com.tcl.gamebar` 3.00.19 |
| PC | NVIDIA GeForce RTX 3070、Windows 11 |
| 接続 | TV の HDMI 1 |

注：`ro.odm.tcl.panel_size` は 55、`ro.boot.series` は C を返したが、実機は 85 型。プラットフォーム共通値と判断した。

## Android の表示層は無関係

- `dumpsys display` / `dumpsys SurfaceFlinger` の表示モードは 3840x2160@60 の 1 つだけ（UI の OSD は 1080p）。
- HDMI 映像は `composition type=SIDEBAND` で SurfaceFlinger を経由しない。Android の 60Hz は HDMI 入力やパネルとは別。

## Game Bar の内部（APK 逆解析）

- 比率：`TvPqManager.setOption(source, 3, "<0|1|2>,2")`（0=16:9、1=21:9、2=32:9）→ サービス `tcl_tv_display`
  （`com.tcl.tv.display.ITvDisplayManagerService`、setOption=185、getOption=186、getPanelFrameRate=140）。
  続けて `TvHdmiController`（`vendor.tcl.tvinput.extend.ITvExtendService/default`）経由で EDID を切替（type 11）。
- 位置：`setOption(source, 5, "<pos>,<y>,2")`。上／中／下／カスタム。下は `1,257,2`。
- `tcl_tv_display` は shell から SELinux で見えない（`service call` は "does not exist"、`dumpsys` は FAILED_TRANSACTION）。
  そのため Game Bar の UI を `input keyevent` で操作して再現した。

## 21:9 選択時の EDID

`libtos_hdmi_service.so` が EDID の基本ブロックの DTD を差し替える（ログ `fpi_edid_set_wide_screen_mode`）。

| 状態 | DTD1 | DTD2 |
|---|---|---|
| 16:9（通常） | 3840x2160@60 | 2560x1440@120 |
| 21:9 | 2560x1080@60（198MHz） | 3840x1600@59.96（521.75MHz） |

- ライブラリ内の文字列：`Default Wide Screen EDID DTD1 2560*1080/60HZ`、`DTD2 3840*1600/60HZ`。
- ハイフレームレートモード ON 時はログが `Wide Screen mode with 144HZ selected` に変わるが、ピクセルクロックは同じ（60Hz のまま）。
  ON にすると DisplayID 拡張（4K144、1080p144、1080p240）が増える。
- HF-VSDB（どの状態でも同じ）：Max_TMDS 600MHz、**Max_FRL_Rate=6（12Gbps×4）**、ALLM、VRR 48–240。

## 位置「下」の正体

```
setScreenLocation() value == 1,257,2
TvDisplayManager::setWideScreenPosition
Display_SetWinRegion graphBuf[3840, 1600], osdbase[3840, 2160], crop[0, 0, 3840, 1600], disp[0, 514, 3840, 1645]
```

入力 3840x1600 を 3840x1645 に拡大し、y=514（下端）に置くだけ。EDID・入力タイミングは変わらない。

## HDMI 受信部（決定的な観測点）

`/sys/devices/platform/mtk_srccap0/mtk_dbg/hdmirx/HDMI_INFO`（shell で読める）。HDMI 1 は "Port 3" 列。

| 状態 | 伝送 | 色形式 | 結果 |
|---|---|---|---|
| 16:9・4K120（Windows が自動選択） | TMDS（LEGACY_20）594MHz | YCbCr 4:2:0 | 表示 |
| 16:9・カスタム 3840x1600@120 | TMDS 404MHz | YCbCr 4:2:0 | 表示 |
| 21:9・3840x1600@59.96 | TMDS 520MHz | 4:4:4 | 表示 |
| 21:9・4K60 | TMDS 592MHz | 4:4:4 | 表示 |
| 21:9・4K120（標準） | **FRL 8G×4** 1188MHz | 4:4:4 | 表示 |
| 21:9・カスタム 3840x1600@120 | **FRL 12G×4** | – | **DE Stable=0（無信号）** |
| 21:9・カスタム 3840x1600@100 | **FRL 12G×4** | – | **無信号** |
| 21:9・カスタム 3840x1600@90（CVT-RB2） | TMDS 588MHz | 4:4:4 | 表示（Game Bar 90.0） |
| 21:9・2560x1080@120 | TMDS 373MHz | 4:4:4 | 表示（Game Bar 120.0） |
| **EDID 上書き（Max FRL 8G）後・21:9・カスタム 3840x1600@120** | **FRL 8G×4** 813MHz | 4:4:4 | **表示（Game Bar 120.0）** |

結論：カスタムタイミングでは NVIDIA が EDID の最大 FRL レート（12G×4）を使い、この環境では 12G が通らない。
EDID の Max_FRL_Rate を 4（8G×4）にすると、同じカスタムタイミングが 8G×4 で通る。

## パネル出力

`/sys/devices/platform/mediatek-drm-tv-kms/mtk_dbg/output_frame_rate`（shell で読める、単位は mHz と推定）

| 入力 | 値 |
|---|---|
| 3840x1600@59.96 | 119926（入力の 2 倍） |
| 4K120 | 120000 |
| 2560x1080@120（21:9・下） | 120002 |
| 3840x1600@90（21:9・下） | 91962 |
| 3840x1600@120（21:9・下、EDID 上書き後） | 120001 |

## その他の観測

- 色形式を NVAPI で 4:2:0 に強制しようとすると、3840x1600@60／4K60 では `-104`（NOT_SUPPORTED）。
- ハイフレームレートモード ON の状態では、16:9 でも 4K120／4K144 が無信号になった（12G が選ばれたためと推定）。
- ハイフレームレートモードの ON/OFF で、HDMI 互換性設定が「自動」→「オン」（`tcl_sys_hdmi_edid_version_hdmi1` 0→3）に書き換わった。
