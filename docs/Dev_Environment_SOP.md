# 開發環境虛擬環境 SOP — 集中隔離架構

> 適用場景：macOS 本機開發，專案位於 OneDrive / iCloud 等雲端同步目錄

---

## 架構目的

將虛擬環境統一存放於 `~/.virtualenvs/`，**與專案程式碼目錄徹底分離**，避免：

- 雲端同步工具（OneDrive / iCloud）掃描並上傳大量 venv 檔案
- Symlink 在同步後失效
- 跨裝置同步導致的 Python 路徑錯誤

---

## 一、系統初始建置（全域僅需執行一次）

```fish
mkdir -p ~/.virtualenvs
```

---

## 二、為新專案建立虛擬環境

```fish
# 建立（以 illumio_monitor 為例）
python3 -m venv ~/.virtualenvs/illumio_env

# 啟動
source ~/.virtualenvs/illumio_env/bin/activate.fish
```

提示字元出現 `(illumio_env)` 代表啟動成功。

---

## 三、套件管理

```fish
# 切換至專案目錄
cd ~/Library/CloudStorage/OneDrive-個人/RD/illumio_monitor

# 依 requirements.txt 安裝
pip install -r requirements.txt

# 安裝單一套件
pip install <套件名稱>

# 匯出目前環境至 requirements.txt
pip freeze > requirements.txt
```

---

## 四、退出虛擬環境

```fish
deactivate
```

---

## 五、環境重置

```fish
deactivate
rm -rf ~/.virtualenvs/illumio_env
# 重建請重新執行步驟二
```

---

## 對應關係

| 專案 | 虛擬環境名稱 |
|:---|:---|
| illumio_monitor | `illumio_env` |

---

> 伺服器部署（Ubuntu / Debian）請參閱 [User_Manual_zh.md](User_Manual_zh.md) 第 1.2 節與第 6.2 節。
