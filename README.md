# 清单 · 近期待办

一个适合手机浏览器的个人待办网页。打开后即可添加、编辑、完成和清空任务，支持快捷截止日期。

## 发布

公开仓库的 Settings → Pages → Deploy from a branch，选择 main 分支和 / (root)，保存后等待 GitHub 给出访问地址。

## 数据保存

默认任务保存在当前浏览器 localStorage 中。可选的「☁ 云同步」使用你自己的 Supabase 项目和邮箱验证码登录，电脑手机登录同一邮箱即可共享清单；配置步骤见 [CLOUD-SYNC.md](CLOUD-SYNC.md)。

登录后可显式导入本机待办，保留本机副本。云端按账号隔离，在线时每 15 秒自动刷新；断网保存会报错并保留输入。清除浏览器数据会删除本机任务；受限预览器的临时模式刷新后会丢失任务。

网站：https://zhehao-wang-ui.github.io/-Joey/

## 字体

包含站酷快乐体，遵循 SIL Open Font License 1.1；完整许可见 FONT-LICENSE.txt，亦嵌入网页内。

云同步使用随页面打包的官方 Supabase JS SDK 2.118.0，许可见 SDK-LICENSES.txt，亦嵌入网页内。网页不加载外部 CDN 脚本。
