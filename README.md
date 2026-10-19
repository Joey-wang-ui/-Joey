# 清单 · 近期待办

一个适合手机浏览器的个人待办网页。打开后即可添加、编辑、完成和清空任务，支持快捷截止日期。

## 发布

公开仓库的 Settings → Pages → Deploy from a branch，选择 main 分支和 / (root)，保存后等待 GitHub 给出访问地址。

## 数据保存

默认任务保存在当前浏览器 localStorage 中。可选的「☁ 云同步」使用你自己的 Supabase 项目和邮箱验证码登录，电脑手机登录同一邮箱即可共享清单；配置步骤见 [CLOUD-SYNC.md](CLOUD-SYNC.md)。

登录后可显式导入本机待办，保留本机副本。云端按账号隔离，在线时每 15 秒自动刷新；断网保存会报错并保留输入。清除浏览器数据会删除本机任务；受限预览器的临时模式刷新后会丢失任务。

网站：https://joey-wang-ui.github.io/-Joey/

## 字体

包含站酷快乐体，遵循 SIL Open Font License 1.1；完整许可见 FONT-LICENSE.txt，亦嵌入网页内。

云同步使用随页面打包的官方 Supabase JS SDK 2.118.0，许可见 SDK-LICENSES.txt，亦嵌入网页内。网页不加载外部 CDN 脚本。

## 管理授权配置

如需由自动流程协助配置 Supabase，在 [新增仓库密钥](https://github.com/Joey-wang-ui/-Joey/settings/secrets/actions/new) 页面，名称填写 `SUPABASE_ACCESS_TOKEN`，Secret 填写 Supabase 管理令牌，再点击 Add secret。密钥不可放入网页或提交进仓库。

已准备只读授权检查工作流 Check Supabase access。保存密钥后可在 Actions 页面手动运行，或由维护者触发。检查仅验证管理 API 并显示组织/项目数量，不输出令牌和资源名称。授权检查通过不代表云同步配置已完成，建表和邮箱配置仍需后续设置。临时管理令牌在配置结束后应撤销。
