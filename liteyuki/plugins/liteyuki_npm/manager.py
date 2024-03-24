import os

import nonebot.plugin
from nonebot import on_command
from nonebot.exception import FinishedException
from nonebot.internal.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna, Alconna, Args, Arparma

from liteyuki.utils.data_manager import GroupChat, InstalledPlugin, User, group_db, plugin_db, user_db
from liteyuki.utils.message import Markdown as md, send_markdown
from liteyuki.utils.permission import GROUP_ADMIN, GROUP_OWNER
from liteyuki.utils.ly_typing import T_Bot, T_MessageEvent
from liteyuki.utils.language import get_user_lang
from .common import get_plugin_can_be_toggle, get_plugin_global_enable, get_plugin_session_enable, get_plugin_default_enable
from .installer import get_store_plugin, npm_update

list_plugins = on_alconna(
    Alconna(
        ['list-plugins', "插件列表", "列出插件"],
    )
)

toggle_plugin = on_alconna(
    Alconna(
        ['enable-plugin', 'disable-plugin'],
        Args['plugin_name', str],
    )
)

global_toggle = on_alconna(
    Alconna(
        ['toggle-global'],
        Args['plugin_name', str],
    ),
    permission=SUPERUSER
)


@list_plugins.handle()
async def _(event: T_MessageEvent, bot: T_Bot):
    if not os.path.exists("data/liteyuki/plugins.json"):
        await npm_update()
    lang = get_user_lang(str(event.user_id))
    reply = f"# {lang.get('npm.loaded_plugins')} | {lang.get('npm.total', TOTAL=len(nonebot.get_loaded_plugins()))} \n***\n"
    for plugin in nonebot.get_loaded_plugins():
        # 检查是否有 metadata 属性
        # 添加帮助按钮
        btn_usage = md.button(lang.get('npm.usage'), f'help {plugin.module_name}', False)
        store_plugin = await get_store_plugin(plugin.module_name)

        session_enable = get_plugin_session_enable(event, plugin.module_name)
        default_enable = get_plugin_default_enable(plugin.module_name)


        if store_plugin:
            btn_homepage = md.link(lang.get('npm.homepage'), store_plugin.homepage)
            show_name = store_plugin.name
            show_desc = store_plugin.desc
        elif plugin.metadata:
            if plugin.metadata.extra.get('liteyuki'):
                btn_homepage = md.link(lang.get('npm.homepage'), "https://github.com/snowykami/LiteyukiBot")
            else:
                btn_homepage = lang.get('npm.homepage')
            show_name = plugin.metadata.name
            show_desc = plugin.metadata.description
        else:
            btn_homepage = lang.get('npm.homepage')
            show_name = plugin.name
            show_desc = lang.get('npm.no_description')

        if plugin.metadata:
            reply += (f"\n**{md.escape(show_name)}**\n"
                      f"\n > {md.escape(show_desc)}")
        else:
            reply += (f"**{md.escape(show_name)}**\n"
                      f"\n > {md.escape(show_desc)}")

        reply += f"\n > {btn_usage}  {btn_homepage}"

        if await GROUP_ADMIN(bot, event) or await GROUP_OWNER(bot, event) or await SUPERUSER(bot, event):
            # 添加启用/停用插件按钮
            cmd_toggle = f"{'disable' if session_enable else 'enable'}-plugin {plugin.module_name}"
            text_toggle = lang.get('npm.disable' if session_enable else 'npm.enable')
            can_be_toggle = get_plugin_can_be_toggle(plugin.module_name)
            btn_toggle = text_toggle if not can_be_toggle else md.button(text_toggle, cmd_toggle)

            reply += f"  {btn_toggle}"

            if await SUPERUSER(bot, event):
                plugin_in_database = plugin_db.first(InstalledPlugin, 'module_name = ?', plugin.module_name)
                # 添加移除插件和全局切换按钮
                global_enable = get_plugin_global_enable(plugin.module_name)
                btn_uninstall = (
                        md.button(lang.get('npm.uninstall'), f'npm uninstall {plugin.module_name}')) if plugin_in_database else lang.get(
                    'npm.uninstall')

                btn_toggle_global_text = lang.get('npm.disable_global' if global_enable else 'npm.enable_global')
                cmd_toggle_global = f'npm toggle-global {plugin.module_name}'
                btn_toggle_global = btn_toggle_global_text if not can_be_toggle else md.button(btn_toggle_global_text, cmd_toggle_global)

                reply += f"  {btn_uninstall}  {btn_toggle_global}"

        reply += "\n\n***\n"
    await send_markdown(reply, bot, event=event)


@toggle_plugin.handle()
async def _(result: Arparma, event: T_MessageEvent, bot: T_Bot):
    if not os.path.exists("data/liteyuki/plugins.json"):
        await npm_update()
    # 判断会话类型
    ulang = get_user_lang(str(event.user_id))
    plugin_module_name = result.args.get("plugin_name")

    toggle = result.header_result == 'enable-plugin'  # 判断是启用还是停用

    session_enable = get_plugin_session_enable(event, plugin_module_name)  # 获取插件当前状态

    default_enable = get_plugin_default_enable(plugin_module_name)  # 获取插件默认状态

    can_be_toggled = get_plugin_can_be_toggle(plugin_module_name)  # 获取插件是否可以被启用/停用

    if not can_be_toggled:
        await toggle_plugin.finish(ulang.get("npm.plugin_cannot_be_toggled", NAME=plugin_module_name))

    if session_enable == toggle:
        await toggle_plugin.finish(
            ulang.get("npm.plugin_already", NAME=plugin_module_name, STATUS=ulang.get("npm.enable") if toggle else ulang.get("npm.disable")))

    if event.message_type == "private":
        session = user_db.first(User, "user_id = ?", event.user_id, default=User(user_id=event.user_id))
    else:
        if await GROUP_ADMIN(bot, event) or await GROUP_OWNER(bot, event) or await SUPERUSER(bot, event):
            session = group_db.first(GroupChat, "group_id = ?", event.group_id, default=GroupChat(group_id=str(event.group_id)))
        else:
            raise FinishedException(ulang.get("Permission Denied"))
    try:
        if toggle:
            if default_enable:
                session.disabled_plugins.remove(plugin_module_name)
            else:
                session.enabled_plugins.append(plugin_module_name)
        else:
            if default_enable:
                session.disabled_plugins.append(plugin_module_name)
            else:
                session.enabled_plugins.remove(plugin_module_name)
        if event.message_type == "private":
            print("已保存")
            user_db.upsert(session)
        else:
            group_db.upsert(session)
    except Exception as e:
        print(e)
        await toggle_plugin.finish(
            ulang.get(
                "npm.toggle_failed",
                NAME=plugin_module_name,
                STATUS=ulang.get("npm.enable") if toggle else ulang.get("npm.disable"),
                ERROR=str(e))
        )

    await toggle_plugin.finish(
        ulang.get(
            "npm.toggle_success",
            NAME=plugin_module_name,
            STATUS=ulang.get("npm.enable") if toggle else ulang.get("npm.disable"))
    )


@run_preprocessor
async def _(event: T_MessageEvent, matcher: Matcher):
    plugin = matcher.plugin
    # TODO 插件启用/停用检查hook
    nonebot.logger.info(f"Plugin Callapi: {plugin.module_name}")
