# meta developer: @smodules

import asyncio
import base64
import io

import aiohttp

from herokutl.types import Message

from .. import loader, utils
from ..inline.types import InlineCall

API_BASE = "https://api.github.com"
SMODULES_REPO = "amreVault/sModules"
SMODULES_BRANCH = "main"
SMODULES_RAW_BASE = f"https://raw.githubusercontent.com/{SMODULES_REPO}/refs/heads/{SMODULES_BRANCH}"
SMODULES_JSDELIVR_URL = f"https://data.jsdelivr.com/v1/packages/gh/{SMODULES_REPO}@{SMODULES_BRANCH}"

E = {
    "gh": '<tg-emoji emoji-id="5296237851891998039">🐙</tg-emoji>',
    "ok": '<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji>',
    "err": '<tg-emoji emoji-id="5985346521103604145">🚫</tg-emoji>',
    "bul": '<tg-emoji emoji-id="6005570495603282482">▪️</tg-emoji>',
    "trash": '<tg-emoji emoji-id="5879896690210639947">🗑</tg-emoji>',
    "link": '<tg-emoji emoji-id="4916086774649848789">🔗</tg-emoji>',
    "gear": '<tg-emoji emoji-id="5877260593903177342">⚙️</tg-emoji>',
    "search": '<tg-emoji emoji-id="5874960879434338403">🔎</tg-emoji>',
}

UE = {
    "gh": '<emoji document_id=5296237851891998039>🐙</emoji>',
    "ok": '<emoji document_id=5985596818912712352>✅</emoji>',
    "err": '<emoji document_id=5985346521103604145>🚫</emoji>',
    "bul": '<emoji document_id=6005570495603282482>▪️</emoji>',
}


@loader.tds
class sEasyGitMod(loader.Module):
    """Скачивай готовые sМодули и управляй своим GitHub-репозиторием прямо в Telegram"""

    strings = {
        "name": "sEasyGit",
        "no_token": f"{UE['err']} <b>Не задан GitHub token</b>\nУстанови его в конфиге: <code>.cfg sEasyGit</code>",
        "main_menu": f"{E['gh']} <b>sEasyGit</b>\n\nВыбери действие",
        "loading": f"{E['gear']} <i>Загрузка...</i>",
        "api_error": f"{E['err']} <b>Ошибка GitHub API:</b>\n<code>{{}}</code>",
        "no_default_repo": "Репозиторий по умолчанию не задан в конфиге",
        "no_local_path": "Локальный путь не задан в конфиге",
        "repo_list_header": f"{E['gh']} <b>Твои репозитории</b>\n\nВыбери репозиторий",
        "repo_info": (
            f"{E['gh']} <b>{{full_name}}</b>\n\n"
            "{description}\n\n"
            "⭐ <b>{stars}</b> · 🍴 <b>{forks}</b> · 🌿 <code>{branch}</code>\n"
            "🗣 {language}"
        ),
        "tree_header": f"{E['gh']} <b>{{}}</b>\n{E['bul']} <code>/{{}}</code>",
        "smodules_header": f"{E['gh']} <b>sМодули</b>\n\nВыбери модуль для скачивания",
        "no_modules": "В репозитории не найдено .py файлов",
        "empty_dir": "Папка пуста",
        "file_info": f"{E['gh']} <b>{{}}</b>\n{E['bul']} <code>{{}}</code>\n💾 {{}} КБ",
        "raw_code": f"{E['link']} <b>Raw-ссылка</b>\n\n<code>{{}}</code>",
        "file_sent": "📥 Файл отправлен",
        "file_send_fail_alert": "Не удалось отправить файл: {}",
        "commits_header": f"📝 <b>Последние коммиты — {{}}</b>\n\n",
        "commit_item": f"{E['bul']} <code>{{}}</code> {{}}\n   <i>{{}}</i>\n\n",
        "issues_header": "🐛 <b>Открытые issues — {}</b>\n\n",
        "issue_item": f"{E['bul']} <b>#{{}}</b> {{}}\n",
        "no_issues": "Открытых issues нет",
        "no_commits": "Коммитов не найдено",
        "starred": "⭐ Добавлено в избранное",
        "unstarred": "💔 Убрано из избранного",
        "pull_running": f"{E['gh']} <i>Выполняю git pull...</i>",
        "pull_result": f"{E['gh']} <b>Git pull завершён</b>\n\n<code>{{}}</code>",
        "issue_created": f"{UE['ok']} <b>Issue создан:</b> {{}}",
        "issue_usage": (
            f"{UE['err']} <b>Использование:</b>\n"
            "<code>.sgitissue owner/repo; заголовок; текст</code>\n"
            "<code>.sgitissue ; заголовок; текст</code> - в репозиторий по умолчанию"
        ),
        "push_usage": (
            f"{UE['gh']} <b>Загрузка файла в репозиторий</b>\n\n"
            "Ответь этой командой на сообщение с файлом:\n"
            "<code>.sgitpush owner/repo; путь/в/репо.py; текст коммита</code>\n"
            "<code>.sgitpush ; путь/в/репо.py; текст коммита</code> - в репозиторий по умолчанию"
        ),
        "push_hint": "Ответь на файл: .sgitpush {}; путь/в/репо.py; текст коммита",
        "install_sent": "Команда установки отправлена в чат",
        "push_no_reply": f"{UE['err']} <b>Ответь на сообщение с файлом</b>",
        "push_done": f"{UE['ok']} <b>Файл загружен</b>\n{{}}",
    }

    strings_ru = strings

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "github_token", "", "Personal Access Token GitHub",
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "default_repo", "", "Репозиторий по умолчанию в формате owner/repo",
            ),
            loader.ConfigValue(
                "local_repo_path", "", "Локальный путь на сервере для git pull",
            ),
        )

    async def client_ready(self, client, db):
        self._client = client
        lm = self.lookup("loader") or self.lookup("Loader")
        self._loader_mod = lm
        self._allmodules = getattr(lm, "allmodules", None)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.config['github_token']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _api(self, method: str, path: str, **kwargs):
        url = f"{API_BASE}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=self._headers(), timeout=20, **kwargs) as resp:
                data = await resp.json() if resp.content_type == "application/json" else {}
                if resp.status >= 400:
                    raise RuntimeError(data.get("message", f"HTTP {resp.status}"))
                return data

    def _main_markup(self, chat_id: int):
        rows = []

        if self.config["default_repo"]:
            rows.append([
                {"text": f"⭐ {self.config['default_repo']}", "callback": self._repo_view, "args": (chat_id, self.config["default_repo"])}
            ])

        rows.append([{"text": "📦 Мои репозитории", "callback": self._repo_list, "args": (chat_id, 0)}])
        rows.append([{"text": "🧩 sМодули", "callback": self._smodules_list, "args": (chat_id,)}])

        row = []
        if self.config["local_repo_path"]:
            row.append({"text": "📥 Git Pull", "callback": self._git_pull, "args": (chat_id,)})
        row.append({"text": "📤 Push файла", "callback": self._push_hint, "args": (chat_id, self.config["default_repo"] or "owner/repo")})
        rows.append(row)

        rows.append([
            {"text": "🔄 Обновить", "callback": self._main_menu, "args": (chat_id,)},
            {"text": "❌ Закрыть", "action": "close"},
        ])

        return rows

    async def _main_menu(self, call: InlineCall, chat_id: int):
        await call.edit(self.strings["main_menu"], reply_markup=self._main_markup(chat_id))

    @loader.command(ru_doc="открыть панель управления GitHub")
    async def sgit(self, message: Message):
        """open the GitHub control panel"""
        await self.inline.form(
            text=self.strings["main_menu"],
            message=message,
            reply_markup=self._main_markup(message.chat_id),
        )

    async def _repo_list(self, call: InlineCall, chat_id: int, page: int):
        if not self.config["github_token"]:
            await call.edit(self.strings["no_token"], reply_markup=self._back_markup(chat_id))
            return

        await call.edit(self.strings["loading"])

        try:
            repos = await self._api("GET", "/user/repos", params={"sort": "updated", "per_page": 100})
        except Exception as e:
            await call.edit(self.strings["api_error"].format(str(e)), reply_markup=self._back_markup(chat_id))
            return

        per_page = 6
        total_pages = max(1, (len(repos) + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        chunk = repos[page * per_page:(page + 1) * per_page]

        rows = []
        for repo in chunk:
            rows.append([{
                "text": repo["full_name"],
                "callback": self._repo_view,
                "args": (chat_id, repo["full_name"]),
            }])

        nav = []
        if page > 0:
            nav.append({"text": "⬅️", "callback": self._repo_list, "args": (chat_id, page - 1)})
        nav.append({"text": f"{page + 1}/{total_pages}", "callback": self._repo_list, "args": (chat_id, page)})
        if page < total_pages - 1:
            nav.append({"text": "➡️", "callback": self._repo_list, "args": (chat_id, page + 1)})
        rows.append(nav)

        rows.append([
            {"text": "⬅️ Назад", "callback": self._main_menu, "args": (chat_id,)},
            {"text": "❌ Закрыть", "action": "close"},
        ])

        await call.edit(self.strings["repo_list_header"], reply_markup=rows)

    def _repo_markup(self, chat_id: int, full_name: str, starred: bool = None):
        star_label = "💔 Unstar" if starred else "⭐ Star"
        rows = [
            [
                {"text": "📁 Файлы", "callback": self._tree_view, "args": (chat_id, full_name, "")},
                {"text": "📝 Коммиты", "callback": self._commits_view, "args": (chat_id, full_name)},
            ],
            [
                {"text": "🐛 Issues", "callback": self._issues_view, "args": (chat_id, full_name)},
                {"text": star_label, "callback": self._toggle_star, "args": (chat_id, full_name)},
            ],
            [
                {"text": "📤 Push файла", "callback": self._push_hint, "args": (chat_id, full_name)},
                {"text": "🌐 Открыть", "url": f"https://github.com/{full_name}"},
            ],
            [
                {"text": "⬅️ Назад", "callback": self._repo_list, "args": (chat_id, 0)},
                {"text": "🔄 Обновить", "callback": self._repo_view, "args": (chat_id, full_name)},
            ],
            [{"text": "❌ Закрыть", "action": "close"}],
        ]
        return rows

    async def _repo_view(self, call: InlineCall, chat_id: int, full_name: str):
        if not self.config["github_token"]:
            await call.edit(self.strings["no_token"], reply_markup=self._back_markup(chat_id))
            return

        await call.edit(self.strings["loading"])

        try:
            repo = await self._api("GET", f"/repos/{full_name}")
            starred = True
            try:
                await self._api("GET", f"/user/starred/{full_name}")
            except Exception:
                starred = False
        except Exception as e:
            await call.edit(self.strings["api_error"].format(str(e)), reply_markup=self._back_markup(chat_id))
            return

        text = self.strings["repo_info"].format(
            full_name=repo["full_name"],
            description=repo.get("description") or "<i>без описания</i>",
            stars=repo.get("stargazers_count", 0),
            forks=repo.get("forks_count", 0),
            branch=repo.get("default_branch", "—"),
            language=repo.get("language") or "—",
        )

        await call.edit(text, reply_markup=self._repo_markup(chat_id, full_name, starred=starred))

    async def _commits_view(self, call: InlineCall, chat_id: int, full_name: str):
        await call.edit(self.strings["loading"])

        try:
            commits = await self._api("GET", f"/repos/{full_name}/commits", params={"per_page": 5})
        except Exception as e:
            await call.edit(self.strings["api_error"].format(str(e)), reply_markup=self._repo_back_markup(chat_id, full_name))
            return

        text = self.strings["commits_header"].format(full_name)
        if not commits:
            text += self.strings["no_commits"]
        else:
            for c in commits:
                sha = c["sha"][:7]
                msg_line = c["commit"]["message"].split("\n")[0][:60]
                author = c["commit"]["author"]["name"]
                text += self.strings["commit_item"].format(sha, msg_line, author)

        await call.edit(text, reply_markup=self._repo_back_markup(chat_id, full_name))

    async def _issues_view(self, call: InlineCall, chat_id: int, full_name: str):
        await call.edit(self.strings["loading"])

        try:
            issues = await self._api("GET", f"/repos/{full_name}/issues", params={"state": "open", "per_page": 5})
        except Exception as e:
            await call.edit(self.strings["api_error"].format(str(e)), reply_markup=self._repo_back_markup(chat_id, full_name))
            return

        text = self.strings["issues_header"].format(full_name)
        issues = [i for i in issues if "pull_request" not in i]

        if not issues:
            text += self.strings["no_issues"]
        else:
            for i in issues:
                text += self.strings["issue_item"].format(i["number"], i["title"][:60])

        await call.edit(text, reply_markup=self._repo_back_markup(chat_id, full_name))

    async def _toggle_star(self, call: InlineCall, chat_id: int, full_name: str):
        try:
            currently_starred = True
            try:
                await self._api("GET", f"/user/starred/{full_name}")
            except RuntimeError:
                currently_starred = False

            if currently_starred:
                await self._api("DELETE", f"/user/starred/{full_name}")
                await call.answer(self.strings["unstarred"])
            else:
                await self._api("PUT", f"/user/starred/{full_name}")
                await call.answer(self.strings["starred"])
        except Exception as e:
            await call.answer(str(e), show_alert=True)
            return

        await self._repo_view(call, chat_id, full_name)

    async def _push_hint(self, call: InlineCall, chat_id: int, full_name: str):
        await call.answer(self.strings["push_hint"].format(full_name), show_alert=True)

    def _back_markup(self, chat_id: int):
        return [
            [{"text": "⬅️ Назад", "callback": self._main_menu, "args": (chat_id,)}],
            [{"text": "❌ Закрыть", "action": "close"}],
        ]

    def _repo_back_markup(self, chat_id: int, full_name: str):
        return [
            [{"text": "⬅️ Назад", "callback": self._repo_view, "args": (chat_id, full_name)}],
            [{"text": "❌ Закрыть", "action": "close"}],
        ]

    async def _tree_view(self, call: InlineCall, chat_id: int, full_name: str, path: str):
        await call.edit(self.strings["loading"])

        try:
            items = await self._api("GET", f"/repos/{full_name}/contents/{path}")
        except Exception as e:
            await call.edit(self.strings["api_error"].format(str(e)), reply_markup=self._repo_back_markup(chat_id, full_name))
            return

        if isinstance(items, dict):
            items = [items]

        items.sort(key=lambda i: (i["type"] != "dir", i["name"].lower()))

        rows = []
        for item in items[:30]:
            icon = "📁" if item["type"] == "dir" else "📄"
            if item["type"] == "dir":
                rows.append([{
                    "text": f"{icon} {item['name']}",
                    "callback": self._tree_view,
                    "args": (chat_id, full_name, item["path"]),
                }])
            else:
                rows.append([{
                    "text": f"{icon} {item['name']}",
                    "callback": self._file_view,
                    "args": (chat_id, full_name, item["path"]),
                }])

        nav_row = []
        if path:
            parent = "/".join(path.split("/")[:-1])
            nav_row.append({"text": "⬆️ Вверх", "callback": self._tree_view, "args": (chat_id, full_name, parent)})
        nav_row.append({"text": "🔄", "callback": self._tree_view, "args": (chat_id, full_name, path)})
        rows.append(nav_row)

        rows.append([
            {"text": "⬅️ К репозиторию", "callback": self._repo_view, "args": (chat_id, full_name)},
            {"text": "❌ Закрыть", "action": "close"},
        ])

        text = self.strings["tree_header"].format(full_name, path)
        if not items:
            text += "\n\n" + self.strings["empty_dir"]

        await call.edit(text, reply_markup=rows)

    async def _file_view(self, call: InlineCall, chat_id: int, full_name: str, path: str):
        await call.edit(self.strings["loading"])

        try:
            item = await self._api("GET", f"/repos/{full_name}/contents/{path}")
        except Exception as e:
            await call.edit(self.strings["api_error"].format(str(e)), reply_markup=self._repo_back_markup(chat_id, full_name))
            return

        size_kb = round(item.get("size", 0) / 1024, 1)
        text = self.strings["file_info"].format(item["name"], path, size_kb)

        parent = "/".join(path.split("/")[:-1])
        rows = [
            [
                {"text": "📥 Скачать файлом", "callback": self._send_file, "args": (chat_id, item["download_url"], item["name"])},
                {"text": "📋 Скопировать raw", "callback": self._copy_raw_tree, "args": (chat_id, full_name, path, item["download_url"])},
            ],
        ]

        if item["name"].endswith(".py"):
            rows.append([{"text": "🧩 Установить модуль", "callback": self._install_module, "args": (chat_id, item["download_url"])}])

        rows.append([{"text": "🌐 Открыть raw", "url": item["download_url"]}])
        rows.append([
            {"text": "⬅️ Назад", "callback": self._tree_view, "args": (chat_id, full_name, parent)},
            {"text": "❌ Закрыть", "action": "close"},
        ])

        await call.edit(text, reply_markup=rows)

    async def _smodules_list(self, call: InlineCall, chat_id: int):
        await call.edit(self.strings["loading"])

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SMODULES_JSDELIVR_URL, timeout=20) as resp:
                    if resp.status >= 400:
                        raise RuntimeError(f"HTTP {resp.status}")
                    data = await resp.json()
        except Exception as e:
            await call.edit(self.strings["api_error"].format(str(e)), reply_markup=self._back_markup(chat_id))
            return

        files = data.get("files", [])
        modules = sorted(
            (f for f in files if f.get("type") == "file" and f["name"].endswith(".py")),
            key=lambda f: f["name"].lower(),
        )

        rows = []
        for item in modules[:50]:
            rows.append([{
                "text": item["name"],
                "callback": self._file_view_public,
                "args": (chat_id, item["name"], item.get("size", 0)),
            }])

        rows.append([
            {"text": "⬅️ Назад", "callback": self._main_menu, "args": (chat_id,)},
            {"text": "🔄 Обновить", "callback": self._smodules_list, "args": (chat_id,)},
        ])
        rows.append([{"text": "❌ Закрыть", "action": "close"}])

        text = self.strings["smodules_header"]
        if not modules:
            text += "\n\n" + self.strings["no_modules"]

        await call.edit(text, reply_markup=rows)

    async def _file_view_public(self, call: InlineCall, chat_id: int, file_name: str, size: int):
        raw_url = f"{SMODULES_RAW_BASE}/{file_name}"
        size_kb = round(size / 1024, 1)
        text = self.strings["file_info"].format(file_name, file_name, size_kb)

        rows = [
            [
                {"text": "📥 Скачать файлом", "callback": self._send_file, "args": (chat_id, raw_url, file_name)},
                {"text": "📋 Скопировать raw", "callback": self._copy_raw_smodules, "args": (chat_id, file_name, size, raw_url)},
            ],
            [{"text": "🧩 Установить модуль", "callback": self._install_module, "args": (chat_id, raw_url)}],
            [{"text": "🌐 Открыть raw", "url": raw_url}],
            [
                {"text": "⬅️ Назад", "callback": self._smodules_list, "args": (chat_id,)},
                {"text": "❌ Закрыть", "action": "close"},
            ],
        ]

        await call.edit(text, reply_markup=rows)

    async def _copy_raw_smodules(self, call: InlineCall, chat_id: int, file_name: str, size: int, raw_url: str):
        text = self.strings["raw_code"].format(raw_url)
        rows = [[{"text": "⬅️ Назад", "callback": self._file_view_public, "args": (chat_id, file_name, size)}]]
        await call.edit(text, reply_markup=rows)

    async def _install_module(self, call: InlineCall, chat_id: int, download_url: str):
        if not self._loader_mod:
            await call.answer("Не найден загрузчик модулей", show_alert=True)
            return

        try:
            sent = await self._client.send_message(chat_id, "...")
            await self._loader_mod.download_and_install(download_url, message=sent)
            await call.answer(self.strings["install_sent"])
        except Exception as e:
            await call.answer(str(e), show_alert=True)

    async def _copy_raw_tree(self, call: InlineCall, chat_id: int, full_name: str, path: str, raw_url: str):
        text = self.strings["raw_code"].format(raw_url)
        rows = [[{"text": "⬅️ Назад", "callback": self._file_view, "args": (chat_id, full_name, path)}]]
        await call.edit(text, reply_markup=rows)

    async def _send_file(self, call: InlineCall, chat_id: int, download_url: str, file_name: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url, timeout=30) as resp:
                    data = await resp.read()

            buf = io.BytesIO(data)
            buf.name = file_name
            await self._client.send_file(chat_id, buf, force_document=True)
            await call.answer(self.strings["file_sent"])
        except Exception as e:
            await call.answer(self.strings["file_send_fail_alert"].format(str(e)), show_alert=True)

    async def _git_pull(self, call: InlineCall, chat_id: int):
        path = self.config["local_repo_path"]
        if not path:
            await call.answer(self.strings["no_local_path"], show_alert=True)
            return

        await call.edit(self.strings["pull_running"])

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", path, "pull",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode(errors="ignore").strip()[:800] or "готово"
        except Exception as e:
            output = str(e)

        await call.edit(self.strings["pull_result"].format(output), reply_markup=self._main_markup(chat_id))

    @loader.command(ru_doc="owner/repo; заголовок; текст - создать issue")
    async def sgitissue(self, message: Message):
        """owner/repo; title; body - create a github issue"""
        if not self.config["github_token"]:
            await utils.answer(message, self.strings["no_token"])
            return

        args = utils.get_args_raw(message)
        if not args or args.count(";") < 2:
            await utils.answer(message, self.strings["issue_usage"])
            return

        repo_part, title, body = [p.strip() for p in args.split(";", maxsplit=2)]
        full_name = repo_part or self.config["default_repo"]

        if not full_name:
            await utils.answer(message, self.strings["no_default_repo"])
            return

        try:
            issue = await self._api(
                "POST", f"/repos/{full_name}/issues",
                json={"title": title, "body": body},
            )
        except Exception as e:
            await utils.answer(message, self.strings["api_error"].format(str(e)))
            return

        await utils.answer(message, self.strings["issue_created"].format(issue["html_url"]))

    @loader.command(ru_doc="ответом на файл: owner/repo; путь/в/репо; текст коммита - загрузить файл в репозиторий")
    async def sgitpush(self, message: Message):
        """reply to a file: owner/repo; path/in/repo; commit message - upload a file to the repo"""
        if not self.config["github_token"]:
            await utils.answer(message, self.strings["no_token"])
            return

        args = utils.get_args_raw(message)
        if not args or args.count(";") < 2:
            await utils.answer(message, self.strings["push_usage"])
            return

        reply = await message.get_reply_message()
        if not reply or not reply.media:
            await utils.answer(message, self.strings["push_no_reply"])
            return

        repo_part, path, commit_message = [p.strip() for p in args.split(";", maxsplit=2)]
        full_name = repo_part or self.config["default_repo"]

        if not full_name:
            await utils.answer(message, self.strings["no_default_repo"])
            return

        file_bytes = await self._client.download_media(reply, file=bytes)
        content_b64 = base64.b64encode(file_bytes).decode()

        sha = None
        try:
            existing = await self._api("GET", f"/repos/{full_name}/contents/{path}")
            sha = existing.get("sha")
        except Exception:
            pass

        payload = {"message": commit_message, "content": content_b64}
        if sha:
            payload["sha"] = sha

        try:
            result = await self._api("PUT", f"/repos/{full_name}/contents/{path}", json=payload)
        except Exception as e:
            await utils.answer(message, self.strings["api_error"].format(str(e)))
            return

        await utils.answer(message, self.strings["push_done"].format(result["commit"]["html_url"]))

