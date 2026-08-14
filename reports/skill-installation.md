# Skill 安装与审计记录

## wechat-article-to-markdown

- 来源：`https://github.com/jackwener/wechat-article-to-markdown`
- 固定 commit：`50b7e63c11a880c991815e4bae6a4a9fb161785a`
- 本地路径：`E:\CodexData\.codex\skills\wechat-article-to-markdown`
- 上游 `SKILL.md` 备份：`private-archive\backups\skills\wechat-article-to-markdown\50b7e63c11a880c991815e4bae6a4a9fb161785a\SKILL.md.upstream`
- 上游备份 SHA256：`994494446F0B25165776E7CC76365BE18EB19ED3E30A60EF37A1E7460614A06B`
- 安装后 `SKILL.md` SHA256：`EA2A7DA6666A5C6950644E0723C2E950287B8D9EF509D64F18C02756FEF47AC2`
- 主脚本 SHA256：`AD1140F23D49A3276ED6F4AC9B08050367BBE64A5F1634CF53F2B8B160319424`
- `pyproject.toml` SHA256：`1139B0828A3AE75BCA908B3D2D0845BBA2D840D28E9E1B75AF1C55683C03B482`
- 校验：`quick_validate.py` 通过。

安装前检查了仓库路径、固定版本、依赖与主脚本。主脚本只访问公开微信文章和图片，未发现令牌读取、Cookie 持久化、上传、删除、Shell 执行或隐藏外发逻辑。依赖为 Camoufox、markdownify、BeautifulSoup 和 httpx。上游根目录没有独立 `LICENSE` 文件，但 README 与 `pyproject.toml` 声明 MIT；因此在第三方声明中保留该来源和许可口径。

为适配当前 Codex 校验器，安装副本把 `author`、`version`、`tags` 移入 `metadata`，并补充上游声明的 `license: MIT`；上游原文件已备份。Camoufox Python 包已锁定为 0.5.4，约 492 MB 的浏览器运行时下载在 5 分钟上限内未完成。随后确认合集原始 URL 的 `chksm` 参数即可稳定直取正文，因此浏览器运行时不是当前批处理的必要依赖。

新安装 skill 通常从下一轮任务开始自动发现；本轮仅直接复用了其转换方法并完成本项目适配。

## dgbl-kb

- 来源：本项目 `skills\dgbl-kb`。
- 安装路径：`E:\CodexData\.codex\skills\dgbl-kb`。
- `SKILL.md` SHA256：`30EB586E985B7E535CFC2469C784EE79BC9D3AB1D705899433323046C7249BFB`。
- `agents\openai.yaml` SHA256：`9C5A667369EE9C1AB9211437FA686FE3AE9DC3D7D58E3308491081C8D8FC3C78`。
- `references\project-layout.md` SHA256：`6CF3221C9C7FEFD54F1E0509AA93E09033EF4F7EE938528E1A4D771F9A37FBF0`。
- 冲突处理：目标目录原先不存在，无覆盖、无同名冲突。
- 校验：在 `PYTHONUTF8=1` 下通过 `skill-creator/scripts/quick_validate.py`；Windows 默认 GBK 下校验脚本不能读取 UTF-8 中文，属于工具编码限制，不是 skill 内容错误。

该 skill 固化本项目的双层归档、`chksm` 保留、断点续跑、图片版权占位、索引与发布闸门。它通常从下一轮任务开始自动发现。
