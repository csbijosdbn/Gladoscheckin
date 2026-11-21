# GLaDOS 自动签到

本仓库的签到程序基于 [上游项目](https://github.com/Devilstore/Glados-Railgun-checkin) 的 8ca67db 版本，支持多域名探测、设备匹配及新版签到流程。原有的运行时间、PushPlus 推送和 500 积分自动兑换设置保留。

## 配置 GitHub Actions

在仓库 Settings → Secrets and variables → Actions 中设置：

- `GLADOS_COOKIE`：原有单账号 Cookie，继续有效。从登录的签到页面的网络请求中复制完整 Cookie。
- `GLADOS_COOKIES`：可选，推荐的多账号 JSON 数组；设置后优先于 `GLADOS_COOKIE`，例如：`[{"name":"账号1","origin":"glados.cloud","cookie":"koa:sess=...; koa:sess.sig=...; gld:sess=...","user-agent":"浏览器的完整 User-Agent"}]`。Cookie 不同域名通常不通用。
- `PUSHPLUS_TOKEN`：可选，原有 PushPlus 通知令牌。也可使用 `PUSHDEER_SENDKEY` 或 `SERVERCHAN_SENDKEY`。
- `GLADOS_EXCHANGE_PLAN`：可选，`plan100`、`plan200` 或 `plan500`。未设置时沿用原有 `plan500`，只有签到成功或重复签到且查询到足够积分时才兑换。设置为 `none` 可关闭自动兑换。
- `GLADOS_VERBOSE`：可选，设为 `true` 输出详细日志。

进入 Actions → GLaDOS Auto Checkin → Run workflow 可手动运行，定时任务每天北京时间 23:00、23:30、次日 00:00 执行。不要将 Cookie 或推送令牌提交到仓库或发给他人。

## 排查无权限

先确认使用的是登录时的域名，并在该域名重新登录，更新 Cookie；建议通过 JSON 的 `origin` 和 `user-agent` 字段填写 Cookie 来源域名及同一浏览器的 User-Agent。Cookie 过期、账号风控或 Cloudflare 验证仍可能导致拒绝，代码无法恢复失效的登录状态。日志中出现 Cloudflare、Turnstile 或 403/429/503 时，可参考 [浏览器扩展说明](extension/README.md) 在真实浏览器中完成验证。

上游脚本对账号业务失败会记录日志和推送，但不一定使 Actions 变红，请检查签到总结。更多功能与配置详见 [上游说明](https://github.com/Devilstore/Glados-Railgun-checkin#readme)。
