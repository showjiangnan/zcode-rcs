# ZCode RCS

用户自行部署的 Python 远程桥接服务，配套完整响应式 ZCode Web UI。执行电脑保持飞鱼版 ZCode 开启，浏览器在电脑或手机上输入同一个端点和密钥，使用已授权工作区的会话、工具、编排、记忆、Git、文件和终端。模型及工具运行在执行电脑；服务器负责认证、设备连接和数据转发。

[English](README.en.md) · [桌面源码与安装](https://github.com/showjiangnan/zcode-feiyu) · [API 与 SDK](docs/API.md) · [部署运维](docs/DEPLOYMENT.md) · [安全与边界](docs/SECURITY.md)

当前配套版本：**RCS / SDK 1.1.2，Web 3.15.2**。本次同步飞鱼版工作流运行设置、进度、日志及保存操作，以及共享 Web 的配套协议；保留会话、模型配置、编排和记忆体验。原生 MCP Apps/Gen UI 页面沙箱只在本地桌面支持，Web 不声明相应原生能力。会话执行与子代理仍复用已连接桌面的 runtime。

共享输入框同步桌面最新交互：模型菜单内有思考与速度滑块，默认标准速度。ChatGPT 订阅只提供目录允许的速度，Teamorouter Responses 按每模型 Fast / Ultrafast 配置提供档位；单／双闪电表示所选速度，成功响应的实际档位单独展示，选择 Fast 不代表服务端实际加速。其他供应商保留原流程。Teamorouter 设置页显示余额、币种与推荐充值入口，推荐不代表合作关系。主动工作未开启时隐藏对应入口。

ChatGPT 订阅使用桌面已经连接的供应来源，远控仅展示脱敏状态、公开模型能力和刷新目录；登录及账号管理仍在桌面完成。共享错误提示保留有界 incomplete 原因，不含原始响应或凭据。本机外部会话导入由 Desktop 完成，远控可在原授权工作区读取和继续已导入会话。本次配套桌面 v3.15.2-feiyu.1，并同步 SuggestedPrompt 的双层开关、逐会话确认和有界候选投影。预测由桌面原 Runtime 生成，手机采用为可编辑草稿，重连不触发额外生成。

codex同款提示词预测器，受制于模型自身能力和速度，可能无法媲美codex的预测效率

## 验证与平台范围

本轮同步正式共享 Web、SDK 与协议资源，执行协议/资产集成与 Python 桥接自动化回归；本机浏览器交互验收沿用历史记录。桌面 CUA 的偏移叠放及关闭联动属于本地桌面能力；远控浏览器不获得原生预览帧、操作系统授权或私有凭据接口。Mac 本机通过不代表当前 Windows 原生构建或实机已验证。本轮桌面 Release 仅提供 macOS arm64，Windows 用户需要自行编译，本版不提供 Windows 安装包；公网 TLS、实体手机软键盘及全部第三方服务仍需各自环境验收。

## 快速开始：本机验证

需要 Python 3.12+ 和 uv。发布目录已包含配套 Web 与 JavaScript SDK，不需要 Node 或 Electron 才能运行服务器。

```bash
uv sync --frozen
uv run zcode-rcs keygen --output data/keys.json --secret-output data/owner.key
export RCS_PUBLIC_ORIGIN=http://127.0.0.1:8030
export RCS_ALLOW_LOOPBACK_HTTP=1
export RCS_KEYS_FILE="$PWD/data/keys.json"
uv run zcode-rcs serve --port 8030
```

`data/owner.key` 是控制凭证，保留在自己的设备；服务器使用 `keys.json` 的 SHA-256 摘要。密钥文件权限为 0600。HTTP 只用于本机 loopback；其他电脑/手机使用自己的 HTTPS 域名。

1. 在支持 RCS 的飞鱼版 ZCode 打开 **设置 → 远程服务 → RCS服务**。
2. 输入端点和生成的密钥，设置设备名称，选择明确允许的工作区，验证连接并保存启用。未选择工作区不会开放目录。
3. 打开桥接端点，输入同一个密钥。选择在线设备、窗口和工作区。
4. 保持桌面 ZCode 开启。电脑睡眠、窗口 Host 退出或网络断开时，Web 显示重连；不会在服务器另起 Agent 或接受离线任务。

## 生产部署

使用独立 origin 根路径，例如 `https://zcode.example.com`。TLS 证书由服务器运营者配置，桌面与浏览器不跳过证书验证。

```bash
export RCS_PUBLIC_ORIGIN=https://zcode.example.com
export RCS_KEYS_FILE="$PWD/data/keys.json"
docker compose -f deploy/compose.yaml up -d --build
```

容器只映射 loopback 8030。将 [Nginx 示例](deploy/nginx.conf) 放入自己的 TLS server 块。单个 Uvicorn worker 持有设备与 attachment 路由，不能直接扩成多 worker。完整配置、备份、升级与轮换见 [部署文档](docs/DEPLOYMENT.md)。

## 可以做什么

| 能力               | 实现和边界                                                                                           |
| ------------------ | ---------------------------------------------------------------------------------------------------- |
| 响应式完整会话 UI  | 复用桌面的 React Root 与组件，电脑/手机浏览器可用；认证不依赖厂商账号                                |
| 会话与编排         | 使用桌面原 runtime 和 admission；支持原有标准/coordinator/swarm、输入、停止、权限、历史与恢复        |
| 记忆、工作流、图片 | 调用 Host 原服务和开关；图片仍使用用户在桌面配置的提供方，不增加云端模型凭据                         |
| 提示预测           | 复用桌面全局开关与逐会话实验确认；原 Runtime 后台生成，手机采用为可编辑草稿，重连恢复不重复生成      |
| 文件与产物         | Host 校验实际路径；附件走原事务协议；媒体分块与 Range；有界文本编辑 API 使用内容哈希防止覆盖冲突     |
| 终端               | PTY 由 Host 持有；断线不杀进程，重新发现/附着原 ID、sequence 回放与去重；输出窗口有界                |
| 独立 API           | REST 控制面、公开 RPC manifest/schema、无 Electron/DOM 依赖的 SDK；支持自定义 fetch/WebSocket 适配器 |
| 自主访问控制       | 本地系统保护密钥、服务端摘要、短期会话、撤销/轮换、Host 工作区允许列表、Origin 与流控                |

本服务不是云端 bot。桌面原生选文件、应用窗口与 OS 权限仍属于执行电脑，不在浏览器伪造；SSH 与移动聊天机器人入口由桌面设置统一管理。微信小程序/App 成品不随本项目提供，开发者可以适配同一套公开 API。

## 源码与产物更新

Python 源码在 `zcode_rcs/`；Web 与 SDK 的权威 TypeScript 源码在桌面主仓库。这里保留可独立部署的 `web/`、`sdk/`、`protocol/`，不维护第二份会话 UI。更新时在桌面主仓库运行：

```bash
ZCODE_ENV=production pnpm --filter @zcode/web build
node scripts/build-rcs-assets.mjs /path/to/zcode-rcs
```

兼容版本为 bridge **1** / RPC codec **1** / Agent wire **3**。入口元数据及 `web/build-info.json` 用于检查配套产物；后者记录配套版本、源码指纹与产物指纹。导出器拒绝缺失或过期的 Web 构建，先验证暂存产物，再替换三组资源；失败时恢复旧资源。生产升级应停止服务、更新完整发布包后重启，并保留 `data/` 与密钥配置。新增内部服务方法不会自动公开，必须更新允许列表。测试与本地规格不属于公开生产提交范围。

## 数据与安全

桥接不保存会话、代码文件、prompt、记忆或终端输出；SQLite 只保存认证与撤销事实，在线路由和有限转发缓冲在内存。打开文件、历史或工具结果时，相应数据会经自建服务器传输。TLS 在自建服务器终止，服务器运营者处于信任边界内；当前没有端到端加密保证。持有有效共享密钥的设备拥有该身份组的控制权限，请不要公开密钥。

Apache-2.0；保留原项目及第三方许可证，见 [LICENSE](LICENSE)、[Web notices](web/THIRD-PARTY-NOTICES.md)。
