# SPDX-FileCopyrightText: 2024 Dragorn421
# SPDX-License-Identifier: CC0-1.0

from __future__ import annotations

import sys
import io
import datetime
import traceback
import sqlite3
import re
from typing import Optional
from pathlib import Path

import discord
import emoji

import botconf
import zoopeeker
import pycpp

"""
/zq SQL
"""


MESSAGE_MAX_LEN = 2000


async def message_send_exception(wh: discord.Webhook, exc: BaseException):
    await wh.send(
        content=(
            "\n".join(
                (
                    "```diff",
                    "-Internal error-",
                    "```" "```",
                    "".join(traceback.format_exception_only(exc))[
                        : MESSAGE_MAX_LEN - 100
                    ],
                    "```",
                )
            )
        ),
        file=discord.File(
            io.BytesIO("".join(traceback.format_exception(exc)).encode()),
            filename=(
                "error_" + datetime.datetime.now(datetime.UTC).isoformat() + ".txt"
            ),
        ),
    )


def discord_monospace_str_len(s: str):
    """
    Returns the width of a string displayed monospace by Discord (using ``)
    For example "abc" is 3, "🐲" is 2.
    """
    # Not sure about keep_zwj=False but shouldn't really matter in our use cases.
    # (this is still very crummy)
    return sum(
        2 if isinstance(token.value, emoji.EmojiMatch) else 1
        for token in emoji.tokenizer.tokenize(s, keep_zwj=False)
    )


def render_datapeek(
    query: str,
    cols: list[str],
    datapeek: list[tuple],
    peek_offset: int,
    data_full_len: int,
):
    tabular_fmted_elems: list[list[str]] = []
    for datapeek_row in datapeek:
        assert len(cols) == len(datapeek_row)
        tabular_fmted_elems.append(list(map(str, datapeek_row)))
    cols_widths: list[int] = []
    for i_col in range(len(cols)):
        MIN_WIDTH = 1
        cols_widths.append(
            max(
                MIN_WIDTH,
                max(
                    (
                        discord_monospace_str_len(tabular_fmted_row[i_col])
                        for tabular_fmted_row in tabular_fmted_elems
                    ),
                    default=MIN_WIDTH,
                ),
            )
        )
    header_layout_col_names_pos: list[int] = []
    for i_col in range(len(cols)):
        header_layout_col_names_pos.append(sum(cols_widths[:i_col]) + i_col)
    i_col = len(cols) - 1
    header_layout_i_cols_by_i_line = [[i_col]]
    i_col -= 1
    while i_col >= 0:
        col_name = cols[i_col]
        col_pos = header_layout_col_names_pos[i_col]
        col_header_space_end = col_pos + len(col_name) + 1
        target_i_line = len(header_layout_i_cols_by_i_line) - 1
        while target_i_line >= 0:
            if col_header_space_end <= min(
                header_layout_col_names_pos[header_layout_i_cols_by_i_line[j][0]]
                for j in range(target_i_line + 1)
            ):
                break
            target_i_line -= 1
        if target_i_line < 0:
            header_layout_i_cols_by_i_line.insert(0, [i_col])
        else:
            header_layout_i_cols_by_i_line[target_i_line].insert(0, i_col)
        i_col -= 1
    header_layout_i_line_by_i_col = {
        i_col: i_line
        for i_line, i_cols in enumerate(header_layout_i_cols_by_i_line)
        for i_col in i_cols
    }
    header_lines = [""] * len(header_layout_i_cols_by_i_line)
    for i_col in range(len(cols)):
        i_line = header_layout_i_line_by_i_col[i_col]
        col_name = cols[i_col]
        col_pos = header_layout_col_names_pos[i_col]

        line = header_lines[i_line]
        line += " " * (col_pos - len(line))
        line += col_name
        header_lines[i_line] = line

        for j in range(i_line + 1, len(header_lines)):
            is_j_last = (j + 1) == len(header_lines)
            line = header_lines[j]
            line += " " * (col_pos - len(line))
            line += "v" if is_j_last else "|"
            header_lines[j] = line

    tabular_fmted_lines = []
    tabular_fmted_lines.extend(
        "|".join(
            elem + " " * (width - discord_monospace_str_len(elem))
            for width, elem in zip(cols_widths, tabular_fmted_row)
        )
        for tabular_fmted_row in tabular_fmted_elems
    )

    frag_query = "\n".join(("```sql", query, "```"))
    frag_table_pre = "```\n"
    frag_table_header = "".join(s + "\n" for s in header_lines)
    frag_table_contents = "".join(s + "\n" for s in tabular_fmted_lines)
    frag_table_suf = "```"
    if datapeek:
        frag_paging_pos = "\n".join(
            (
                "```",
                f"{peek_offset+1}-{peek_offset+len(datapeek)} / {data_full_len}",
                "```",
            )
        )
    else:
        frag_paging_pos = "```(no results)```"

    combinations = (
        (
            frag_query,
            frag_table_pre,
            frag_table_header,
            frag_table_contents,
            frag_table_suf,
            frag_paging_pos,
        ),
        (
            frag_table_pre,
            frag_table_header,
            frag_table_contents,
            frag_table_suf,
            frag_paging_pos,
        ),
        (
            frag_query,
            frag_table_pre,
            frag_table_contents,
            frag_table_suf,
            frag_paging_pos,
        ),
        (
            frag_table_pre,
            frag_table_contents,
            frag_table_suf,
            frag_paging_pos,
        ),
        (
            frag_table_pre,
            frag_table_contents,
            frag_table_suf,
        ),
    )

    msg = None

    for comb in combinations:
        candidate_msg = "".join(comb)
        if len(candidate_msg) <= MESSAGE_MAX_LEN:
            msg = candidate_msg
            break
    if msg is None:
        for n_lines in range(len(tabular_fmted_lines), 0, -1):
            assert n_lines != 0
            candidate_msg = (
                frag_table_pre
                + "".join(s + "\n" for s in tabular_fmted_lines[:n_lines])
                + frag_table_suf
                + f"{peek_offset+1}-{peek_offset+n_lines} / {data_full_len}",
            )
            if len(candidate_msg) <= MESSAGE_MAX_LEN:
                msg = candidate_msg
                break
    if msg is None:
        msg = "Can't fit even one line of the result in a message"

    return msg


class DataPeekScrollButton(discord.ui.Button):
    def __init__(
        self,
        dpview: DataPeekView,
        scroll_by: int,
        row: int,
    ):
        super().__init__(label=f"{scroll_by:+}", row=row)
        self.dpview = dpview
        self.scroll_by = scroll_by

    async def callback(self, interaction):
        self.dpview.scroll_by(self.scroll_by)
        await interaction.response.edit_message(content=self.dpview.render())


class DataPeekNRowsSelect(discord.ui.Select):
    def __init__(
        self,
        dpview: DataPeekView,
        values: tuple[int],
        default_value: int,
        row: int,
    ):
        super().__init__(
            options=[
                discord.SelectOption(
                    label=f"{v}",
                    value=f"{v}",
                    default=(v == default_value),
                )
                for v in values
            ],
            row=row,
        )
        self.dpview = dpview

    async def callback(self, interaction):
        assert len(self.values) == 1
        selected_value_str = self.values[0]
        selected_value_int = int(selected_value_str)
        self.dpview.set_n_rows(selected_value_int)
        for opt in self.options:
            opt.default = opt.value == selected_value_str
        await interaction.response.edit_message(
            content=self.dpview.render(),
            view=self.view,
        )


class DataPeekDeleteButton(discord.ui.Button):
    def __init__(self, row: int):
        super().__init__(emoji="🗑️", row=row)

    async def callback(self, interaction):
        await interaction.message.delete()


class DataPeekView(discord.ui.View):
    def __init__(
        self,
        query: str,
        cols: list[str],
        data: list[tuple],
    ):
        super().__init__(timeout=300)
        self.query = query
        self.cols = cols
        self.data = data
        self.i_start = 0
        self.n_rows = 10
        self.add_item(DataPeekScrollButton(self, -1, 0))
        self.add_item(DataPeekScrollButton(self, -10, 0))
        self.add_item(DataPeekScrollButton(self, -50, 0))
        self.add_item(DataPeekDeleteButton(0))
        self.add_item(DataPeekScrollButton(self, 1, 1))
        self.add_item(DataPeekScrollButton(self, 10, 1))
        self.add_item(DataPeekScrollButton(self, 50, 1))
        self.add_item(DataPeekNRowsSelect(self, (1, 5, 10, 20, 50), self.n_rows, 2))

        self.wm = None

    def set_wm(self, wm: discord.WebhookMessage):
        self.wm = wm

    async def on_timeout(self):
        if self.wm is not None:
            await self.wm.edit(view=None)

    def render(self):
        datapeek = self.data[self.i_start :][: self.n_rows]
        return render_datapeek(
            self.query,
            self.cols,
            datapeek,
            self.i_start,
            len(self.data),
        )

    def scroll_by(self, n: int):
        self.i_start += n
        if self.i_start < 0:
            self.i_start = 0
        if self.i_start >= len(self.data):
            self.i_start = len(self.data) - 1

    def set_n_rows(self, n: int):
        assert n > 0
        self.n_rows = n


cpp_context = (Path(__file__).parent / "cpp_context.sql").read_text()


async def zooquery_command(
    interaction: discord.Interaction,
    query: str,
    show_cpp_query: bool = False,
):
    await interaction.response.defer(thinking=True)

    try:
        user_discord = interaction.user

        initial_query = query
        user_cpp_context = cpp_context.format(
            discord_user_name=user_discord.name,
        )
        try:
            query = pycpp.my_preprocess(user_cpp_context + "\n" + query)
        except pycpp.ForbiddenUsage as e:
            await interaction.followup.send(f"pycpp.ForbiddenUsage: {e}")
            return

        user = zpk.get_user(user_discord.id)
        if user is None:
            user = zpk.add_user(
                user_discord.id,
                user_discord.name,
                user_discord.display_name,
            )

        con = zpk.dbh.get_user_con(user)

        try:
            cur = con.execute(query)
        except sqlite3.OperationalError as e:
            sqlite_errorname = getattr(e, "sqlite_errorname", None)

            msg = "\n".join(
                (
                    "```diff",
                    (
                        "-Error-"
                        if sqlite_errorname is None
                        else f"-Error ({sqlite_errorname})-"
                    ),
                    "```" "```",
                    (
                        e.args[0]
                        if len(e.args) == 1 and isinstance(e.args[0], str)
                        else repr(e.args)
                    ),
                    "```",
                )
            )

            msg_frag_query = "\n".join(
                (
                    "```sql",
                    query if show_cpp_query else initial_query,
                    "```",
                )
            )
            if len(msg) + len(msg_frag_query) <= MESSAGE_MAX_LEN:
                msg += msg_frag_query

            if len(msg) > MESSAGE_MAX_LEN:
                msg = msg[:MESSAGE_MAX_LEN]

            await interaction.followup.send(msg)
        else:
            cols: list[str] = [item[0] for item in cur.description]
            data = cur.fetchall()

            is_magic = False

            if cols == ["magic_lines"]:
                text = "\n".join(str(v) for (v,) in data)
                if text != "" and len(text) <= MESSAGE_MAX_LEN:
                    is_magic = True
                    await interaction.followup.send(text)

            if not is_magic:
                view = DataPeekView(
                    query if show_cpp_query else initial_query, cols, data
                )

                wm = await interaction.followup.send(
                    view.render(), view=view, wait=True
                )
                view.set_wm(wm)

    except:
        await message_send_exception(interaction.followup, sys.exception())
        raise


async def peek_command(
    interaction: discord.Interaction, target: Optional[discord.User]
):
    await interaction.response.defer(thinking=True)

    try:
        if target is None:
            user_discord = interaction.user
        else:
            user_discord = target
        user = zpk.get_user(user_discord.id)
        if user is None:
            user = zpk.add_user(
                user_discord.id,
                user_discord.name,
                user_discord.display_name,
            )
            await interaction.followup.send("Data created (first peek!)")
        else:
            zpk.refresh_user_data(user)
            await interaction.followup.send("Data refreshed after a good peek")
    except:
        await message_send_exception(interaction.followup, sys.exception())
        raise


async def peekall_command(interaction: discord.Interaction):
    await interaction.response.send_message("Peeking all...")

    try:
        discord_user_ids = botconf.discord_user_ids
        for i, (name, discord_id) in enumerate(discord_user_ids.items()):
            await interaction.edit_original_response(
                content=f"Peeking all... {i+1}/{len(discord_user_ids)} {name}"
            )
            user = await interaction.client.fetch_user(discord_id)
            assert user is not None
            zpk_user = zpk.get_user(discord_id)
            if zpk_user is None:
                zpk.add_user(discord_id, user.name, user.display_name)
            else:
                zpk.refresh_user_data(zpk_user)

    except:
        await message_send_exception(interaction.followup, sys.exception())
        raise
    finally:
        await interaction.edit_original_response(content="Peeking all done")


DELAY_BETWEEN_DUMPS = datetime.timedelta(minutes=1)
datetime_next_dump = datetime.datetime.now()


async def dbdump_command(interaction: discord.Interaction):
    global datetime_next_dump
    now = datetime.datetime.now()
    if now < datetime_next_dump:
        await interaction.response.send_message(
            f"Wait to dump again: <t:{1+int(datetime_next_dump.timestamp())}:R>",
            ephemeral=True,
        )
        return
    datetime_next_dump = now + DELAY_BETWEEN_DUMPS

    await interaction.response.defer(thinking=True)

    try:
        db_dump = dbh.dump()
        db_backup = dbh.backup()
        await interaction.followup.send(
            "Here:",
            files=(
                discord.File(io.BytesIO(db_dump.encode()), "db_dump.sql"),
                discord.File(io.BytesIO(db_backup), "db_backup.sqlite"),
            ),
        )
    except:
        await message_send_exception(interaction.followup, sys.exception())
        raise


class MyClient(discord.Client):
    async def on_ready(self):
        print("Logged on as", self.user)

        self.zpkdr = zoopeeker.ZooPeekerDataRefresher(zpk, self.loop.call_soon)
        self.zpkdr.start()
        # TODO zpkdr.stop()

        tree = discord.app_commands.CommandTree(self)

        command = discord.app_commands.Command(
            name="zq",
            description="Zoo Query",
            callback=zooquery_command,
        )
        tree.add_command(command)

        command = discord.app_commands.Command(
            name="peek",
            description="Take a peek",
            callback=peek_command,
        )
        tree.add_command(command)

        command = discord.app_commands.Command(
            name="peekall",
            description="Take a peek on everyone",
            callback=peekall_command,
        )
        tree.add_command(command)

        command = discord.app_commands.Command(
            name="dbdump",
            description="Download the current database",
            callback=dbdump_command,
        )
        tree.add_command(command)

        await tree.sync()

        print("Reafy-reafy")

    async def on_message(self, message: discord.Message):
        if message.author.id == botconf.zoo_bot_user_id:
            user_discord = None
            if message.interaction is not None:
                # Message results from a slash command run by the interaction user
                user_discord = message.interaction.user
            else:
                # Message is a reply, typically from interacting with a previous zoo message
                # Go up the reply chain until finding an interaction
                # (it isn't guaranteed that the top interaction user then is the one we
                #  want (e.g. /shop buttons can be used by anyone), but good enough)
                ref = message.reference
                while ref is not None:
                    ref_msg = ref.cached_message
                    if ref_msg is None:
                        break
                    if ref_msg.author.id != botconf.zoo_bot_user_id:
                        break
                    if ref_msg.interaction is not None:
                        user_discord = ref_msg.interaction.user
                        break
                    else:
                        ref = ref_msg.reference

            if user_discord is not None:
                user = zpk.get_user(user_discord.id)
                if user is not None:
                    client.zpkdr.notify_activity(user)

                    self.try_parse_todo(user, message.content)

    def try_parse_todo(self, user: zoopeeker.User, msg: str):
        msg_lines = msg.splitlines()
        try:
            i = msg_lines.index("__**Upcoming Events**__")
        except ValueError:
            return
        else:
            i_start_upcoming = i + 1
        try:
            i_end_upcoming = msg_lines.index("")
        except ValueError:
            i_end_upcoming = len(msg_lines)
        lines_upcoming = msg_lines[i_start_upcoming:i_end_upcoming]
        times_by_thing = dict()
        for lu in lines_upcoming:
            m = re.match(r"^>\s[^\s]*\s([^:]+):[^(]+\(<t:(\d+)>\)$", lu)

            if m is None:
                print("Unexpected line format", lu)
                return

            thing = m[1]
            timestamp_str = m[2]
            timestamp = int(timestamp_str)
            time = datetime.datetime.fromtimestamp(timestamp, datetime.UTC)

            times_by_thing[thing] = time

        now = datetime.datetime.now(datetime.UTC)
        for thing, time in times_by_thing.items():
            print(thing, "[at]", time, "[in]", time - now)
        zpk.set_current_profile_todos(user, times_by_thing)


intents = discord.Intents.none()
intents.message_content = True
intents.guild_messages = True
client = MyClient(intents=intents)

# https://discord.com/oauth2/authorize?client_id=1230252029235171328&permissions=265280&integration_type=0&scope=bot
with zoopeeker.DatabaseHandler() as dbh:
    zpk = zoopeeker.ZooPeeker(dbh)
    client.run(botconf.token)
