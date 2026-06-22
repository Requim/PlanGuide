# PlanManager

PlanManager 是一个独立的通用计划书架系统。

- `/plan`：静态前端，登录后进入“我的书架”
- `/plan/api`：账号、模板、Excel 导入、计划实例和状态保存 API
- 支持系统 JSON 模板和 Excel 引导式导入
- 登录账号下可保留多个计划实例，退出后再次登录仍可恢复

## 本地启动

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn planguide.interface.app:app --host 127.0.0.1 --port 8010
```

打开 `http://127.0.0.1:8010/plan`。

默认邀请码为 `change-me`，生产环境必须通过 `PLAN_INVITE_CODE` 覆盖。

## 测试

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m compileall planguide -q
```

## Docker 部署

```bash
cp .env.example .env
docker compose up -d --build
```

`docker-compose.yml` 会启动两个容器：

- `planguide-app`：FastAPI 应用和计划 API。
- `planguide-nginx`：新增的 PlanManager 专用 nginx，监听宿主机 `127.0.0.1:8010`。

如果公网入口是 Caddy，把 `deploy/caddy/planguide-handles.conf` 里的 `handle /plan*` 放在原有兜底转发前，并确保 `planguide-nginx` 和 Caddy 在同一个 Docker 网络。

默认外部网络名是 `unlimitworld_default`。本地单独试 Docker 时，如果没有这个网络，可先执行：

```bash
docker network create unlimitworld_default
```
