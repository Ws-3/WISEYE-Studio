# 两台电脑人工 Git 操作

推荐用 git clone。GitHub Code → Download ZIP 可用于运行，但没有 .git 历史，不能直接 pull/push。仓库使用 main，普通 Git 存储，无需 LFS。

## 第一次下载

安装 Git，在 PowerShell 执行：

```powershell
cd E:\Projects
git clone https://github.com/Ws-3/WISEYE-Studio.git
cd WISEYE-Studio
git status
```

随后按 [DESKTOP.md](DESKTOP.md) 配置 UE 引擎路径、VS 工具链和 Python .venv，再启动 UE、点击播放、启动桌面窗口。

## 每次开始：下载另一台电脑成果

先保存并关闭 UE 和桌面窗口，再执行：

```powershell
cd E:\Projects\WISEYE-Studio
git status
git pull --ff-only
```

若 status 显示自己尚未提交的修改，先提交自己的工作；不要用 reset --hard 丢弃。若 pull 提示分叉，停止覆盖操作，保留当前变更并处理冲突。同一地图、材质等二进制资源建议两台电脑轮流编辑。

## 每次结束：上传本机成果

在 UE 停止播放并“保存全部”，关闭编辑器，再检查并提交：

```powershell
cd E:\Projects\WISEYE-Studio
git status
git diff --stat
git add apps core configs scripts tests ue5 docs Models README.md AGENTS.md WISEYE_ProjectPlan.md .gitignore .gitattributes requirements.txt Start-Desktop.cmd Start-WISEYE.cmd
git diff --cached --stat
git diff --cached --check
git commit -m "说明这次完成的功能"
git push origin main
```

上面的 add 列出工程路径；提交前仍需检查暂存列表，不要上传临时测试物体、凭据或个人资料。Content/__ExternalActors__ 和 __ExternalObjects__ 与地图一起保存/上传，否则另一台电脑可能缺场景修改。papers 为本机未跟踪资料，本次不上传；不要直接 git add .。

第一次 push 可能打开 GitHub 登录，用自己的 Ws-3 账号完成浏览器认证。不要把密码或访问令牌写到代码中。push 被拒绝若因为远端已有新提交，先 fetch，检查并合并；不要 force push。

## 更新后运行

双击 Start-WISEYE.cmd：重新编译本机 C++ 并打开关卡，点击播放。再双击 Start-Desktop.cmd 并连接 UE。
如果 requirements.txt 更新，再运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

UE 引擎、VS、Python 环境各机单独安装。Git 不同步 .venv、Binaries、Intermediate、Saved、日志、备份、机器专用引擎路径；实验 PNG 留在本机 Saved/WISEYE。

## 手工清理临时备份与日志

保存并关闭 UE 与桌面窗口，运行下面命令。省略 -Apply 只预览。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Clean-Temporary.ps1 -Apply
```

只清理仓库 runtime、日志和指定临时缓存；保留模型、papers、环境、编译产物和 Saved/WISEYE 实验输出。
