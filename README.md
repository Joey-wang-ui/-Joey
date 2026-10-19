# 清单 · 近期待办

网站：https://joey-wang-ui.github.io/-Joey/

适合电脑、手机浏览器的个人待办网页，支持快捷截止日期、编辑、完成和批量清空。

## 云同步已配置

点击右上角「☁ 云同步」，输入注册 Supabase 时使用的邮箱，点击「发送登录邮件」，再打开邮件里的登录链接。同一邮箱可在电脑和手机共享清单。项目公开配置已内置在网页中。

当前采用免费默认邮件链接登录。默认测试发信服务限制收件人和发送频率，请先用创建项目的账号邮箱测试。数字验证码需要先在 Supabase 配置自定义 SMTP，再重新运行配置流程。完整说明见 [CLOUD-SYNC.md](CLOUD-SYNC.md)。

## 数据保存

未登录时使用本机浏览器存储。登录后可显式导入本机待办，本机副本保留。云端按账号隔离；在线时每 15 秒自动刷新。断网保存会报错并保留输入。清除浏览器数据会删除本机任务；临时预览模式刷新后会丢失任务。

## 项目维护

Pages 使用 main 分支根目录。临时 Supabase 管理令牌保存在仓库 Secret `SUPABASE_ACCESS_TOKEN`，不写入网页或日志。工作流 Check Supabase access 只读验证管理授权；Configure todo cloud 创建或复用专用 Free 项目，配置表和邮件登录。设置与验收后可撤销临时令牌；日常同步使用用户登录会话。

## 开源许可

站酷快乐体遵循 SIL Open Font License 1.1，见 FONT-LICENSE.txt；官方 Supabase JS SDK 的许可见 SDK-LICENSES.txt。许可证也已嵌入单文件网页，页面不从 CDN 加载脚本。
