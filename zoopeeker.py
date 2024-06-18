# SPDX-FileCopyrightText: 2024 Dragorn421
# SPDX-License-Identifier: CC0-1.0

from __future__ import annotations

from pathlib import Path
import tempfile
import sqlite3
import itertools
import uuid
import threading
import queue
import datetime
import functools

import zooapi
from zooapi import ZooAnimal, ZooAnimalCommon, ZooAnimalRare


class User:
    def __init__(
        self,
        name: str,  # for debug purposes
        discord_id: str,
        user_id: int,
        profile_id_by_profile_zoo_id: dict[str, int],
    ):
        self.name = name
        self.discord_id = discord_id
        self.user_id = user_id
        self.profile_id_by_profile_zoo_id = profile_id_by_profile_zoo_id

    def __str__(self):
        return f"User<{self.name}>"


class DatabaseHandlerTransactionCM:
    i = 0

    def __init__(self, con: sqlite3.Connection):
        self.con = con
        uuid_str = str(uuid.uuid4()).replace("-", "_")
        self.savepoint_name = f"savepoint_together_{self.__class__.i}_{uuid_str}"
        self.__class__.i += 1
        con.rollback()

    def __enter__(self):
        # FIXME idk, autocommit is a mess.
        # it seems fixed in Python 3.12, but I have python 3.11
        # (I want manual commit handling)
        return
        self.con.execute("SAVEPOINT " + self.savepoint_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return
        exit_ok = exc_type is None
        self.con.execute(
            ("RELEASE " if exit_ok else "ROLLBACK TO ") + self.savepoint_name
        )


class DatabaseHandler:
    def __init__(self):
        pass

    def __enter__(self):
        self.tempdir = tempfile.TemporaryDirectory(Path(__file__).stem)
        self.path = Path(self.tempdir.name) / "db.sqlite"
        self.uri = self.path.as_uri()

        self.con_rw = sqlite3.connect(
            self.uri,
            isolation_level=None,
            uri=True,
        )

        self.user_cons: dict[User, sqlite3.Connection] = dict()

        self.animal_ids = self._init_tables()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.con_rw.close()
            self.con_rw = None
            for user_con in self.user_cons.values():
                user_con.close()
            self.user_cons = None
        finally:
            self.tempdir.cleanup()
            self.tempdir = None

    def _init_tables(self):
        # It is unclear to me why but no need to begin/commit a transaction for CREATE TABLE
        self.con_rw.executescript(
            """
            CREATE TABLE "users" (
                "user_id"           INTEGER NOT NULL UNIQUE,
                "discord_id"        TEXT    NOT NULL,
                "user_name"         TEXT    NOT NULL,
                "user_display_name" TEXT    NOT NULL,
                PRIMARY KEY("user_id" AUTOINCREMENT)
            );
            CREATE TABLE "profiles" (
                "profile_id"     INTEGER NOT NULL UNIQUE,
                "user_id"        INTEGER NOT NULL,
                "profile_zoo_id" TEXT    NOT NULL,
                "profile_name"   TEXT    NOT NULL,
                PRIMARY KEY("profile_id" AUTOINCREMENT),
                FOREIGN KEY("user_id") REFERENCES "users"("user_id")
            );
            CREATE TABLE "animals" (
                "animal_id"     INTEGER NOT NULL UNIQUE,
                "animal_name"   TEXT    NOT NULL,
                "animal_emoji"  TEXT    NOT NULL,
                "is_rare"       INTEGER NOT NULL,
                "animal_common" INTEGER NOT NULL,
                "animal_rare"   INTEGER NOT NULL,
                PRIMARY KEY("animal_id" AUTOINCREMENT)
                FOREIGN KEY("animal_common") REFERENCES "animals"("animal_id")
                FOREIGN KEY("animal_rare") REFERENCES "animals"("animal_id")
            );
            CREATE TABLE "zoos" (
                "profile_id" INTEGER NOT NULL,
                "animal_id"  INTEGER NOT NULL,
                "amount"     INTEGER NOT NULL,
                "amount_now" INTEGER NOT NULL,
                FOREIGN KEY("profile_id") REFERENCES "profiles"("profile_id"),
                FOREIGN KEY("animal_id") REFERENCES "animals"("animal_id")
            );
            CREATE TABLE "todos" (
                profile_id   INTEGER NOT NULL,
                thing        TEXT    NOT NULL,
                utctimestamp INTEGER NOT NULL,
                utcdatetime  TEXT    NOT NULL,
                FOREIGN KEY("profile_id") REFERENCES "profiles"("profile_id")
            );
            """
        )

        self.con_rw.execute("BEGIN")

        self.con_rw.executemany(
            "INSERT INTO"
            " animals (animal_name, animal_emoji, is_rare, animal_common, animal_rare)"
            " VALUES (?, ?, ?, ?, ?)",
            itertools.chain(
                (
                    # commons
                    (
                        za.animal_name,
                        za.emoji,
                        False,
                        0,
                        0,
                    )
                    for za in ZooAnimalCommon
                ),
                (
                    # rares
                    (
                        za.animal_name,
                        za.emoji,
                        True,
                        0,
                        0,
                    )
                    for za in ZooAnimalRare
                ),
            ),
        )
        # set common, rare ids for rares
        self.con_rw.execute("UPDATE animals SET animal_rare = animal_id WHERE is_rare")
        self.con_rw.executemany(
            "UPDATE animals"
            " SET animal_common = (SELECT animals_inner.animal_id FROM animals AS animals_inner WHERE animals_inner.animal_name == ?)"
            " WHERE animal_name == ?",
            (
                (
                    za.animal_common.animal_name,
                    za.animal_name,
                )
                for za in ZooAnimalRare
            ),
        )
        # set common, rare ids for commons
        self.con_rw.execute(
            "UPDATE animals SET animal_common = animal_id WHERE NOT is_rare"
        )
        self.con_rw.execute(
            "UPDATE animals AS animals_outer"
            " SET animal_rare = ("
            "   SELECT animals_inner.animal_id"
            "   FROM animals as animals_inner"
            "   WHERE animals_inner.is_rare"
            "     AND animals_inner.animal_common == animals_outer.animal_id"
            " )"
            " WHERE NOT animals_outer.is_rare"
        )

        self.con_rw.execute("COMMIT")

        animal_ids: dict[ZooAnimal, int] = dict()
        for animal_id, animal_name in self.con_rw.execute(
            "SELECT animal_id, animal_name FROM animals"
        ):
            za = ZooAnimal.by_animal_name[animal_name]
            animal_ids[za] = animal_id

        return animal_ids

    def transaction(self):
        return DatabaseHandlerTransactionCM(self.con_rw)

    def add_user(self, discord_id: str, user_name: str, user_display_name: str):
        cur = self.con_rw.cursor()
        cur.execute(
            "SELECT * FROM users WHERE discord_id = ?",
            (discord_id,),
        )
        users_with_discord_id = cur.fetchall()
        if users_with_discord_id:
            raise Exception(
                "user already in db",
                discord_id,
                users_with_discord_id,
            )

        cur = self.con_rw.cursor()
        cur.execute(
            "INSERT INTO"
            " users (discord_id, user_name, user_display_name)"
            " VALUES (?, ?, ?)",
            (discord_id, user_name, user_display_name),
        )
        user_id = cur.lastrowid
        return user_id

    def add_profile(
        self,
        user_id: int,
        profile_zoo_id: str,
        profile_name: str,
        animals_amount: dict[ZooAnimal, int],
        animals_amount_now: dict[ZooAnimal, int],
    ):
        cur = self.con_rw.cursor()
        cur.execute(
            "INSERT INTO"
            " profiles (user_id, profile_zoo_id, profile_name)"
            " VALUES (?, ?, ?)",
            (user_id, profile_zoo_id, profile_name),
        )
        profile_id = cur.lastrowid

        self._insert_zoo_animals(cur, profile_id, animals_amount, animals_amount_now)

        return profile_id

    def _insert_zoo_animals(
        self,
        cur: sqlite3.Cursor,
        profile_id: int,
        animals_amount: dict[ZooAnimal, int],
        animals_amount_now: dict[ZooAnimal, int],
    ):
        cur.executemany(
            "INSERT INTO"
            " zoos (profile_id, animal_id, amount, amount_now)"
            " VALUES (?, ?, ?, ?)",
            (
                (
                    profile_id,
                    self.animal_ids[za],
                    animals_amount.get(za, 0),
                    animals_amount_now.get(za, 0),
                )
                for za in itertools.chain(ZooAnimalCommon, ZooAnimalRare)
            ),
        )

    def remove_profile(self, profile_id: int):
        cur = self.con_rw.cursor()
        cur.execute("DELETE FROM profiles WHERE profile_id = ?", (profile_id,))
        self._delete_zoo_animals(cur, profile_id)

    def _delete_zoo_animals(self, cur: sqlite3.Cursor, profile_id: int):
        cur.execute("DELETE FROM zoos WHERE profile_id = ?", (profile_id,))

    def update_profile(
        self,
        profile_id: int,
        profile_name: str,
        animals_amount: dict[ZooAnimal, int],
        animals_amount_now: dict[ZooAnimal, int],
    ):
        cur = self.con_rw.cursor()
        cur.execute(
            "UPDATE profiles SET profile_name = ? WHERE profile_id = ?",
            (profile_name, profile_id),
        )
        self._delete_zoo_animals(cur, profile_id)
        self._insert_zoo_animals(cur, profile_id, animals_amount, animals_amount_now)

    def set_profile_todos(
        self,
        profile_id: int,
        times_by_thing: dict[str, datetime.datetime],
    ):
        cur = self.con_rw.cursor()
        cur.execute("DELETE FROM todos WHERE profile_id = ?", (profile_id,))
        cur.executemany(
            "INSERT INTO"
            " todos (profile_id, thing, utctimestamp, utcdatetime)"
            " VALUES (?, ?, ?, ?)",
            (
                (
                    profile_id,
                    thing,
                    round(time.timestamp()),
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                )
                for thing, time in times_by_thing.items()
            ),
        )

    def get_user_con(self, user: User):
        user_con = self.user_cons.get(user)
        if user_con:
            return user_con
        # https://www.sqlite.org/uri.html
        user_con = sqlite3.connect(
            self.uri + "?mode=ro",
            uri=True,
        )
        self.user_cons[user] = user_con
        return user_con

    def dump(self):
        return "".join(line + "\n" for line in self.con_rw.iterdump())

    def backup(self):
        return self.path.read_bytes()


class ZooPeekerDataRefresher:
    def __init__(self, zpk: ZooPeeker, call_soon):
        self.zpk = zpk
        self.call_soon = call_soon
        self.queue = queue.Queue()
        self.keep_running = threading.Event()
        self.keep_running.set()

    def notify_activity(self, user: User):
        print("notify_activity", user)
        self.queue.put(user)

    def start(self):
        self.thread = threading.Thread(
            target=self._run,
            name=repr(self),
        )
        self.thread.start()

    def stop(self):
        self.keep_running.clear()
        self.queue.put(None)
        self.thread.join()

    def _refresh_impl(self, user):
        try:
            self.zpk.refresh_user_data(user)
        except:
            print("_refresh_impl: refresh_user_data failed, rescheduling", user)
            self.notify_activity(user)
            raise

    def _call_refresh_sync(self, user):
        print("_call_refresh_sync", user)
        self.call_soon(self._refresh_impl, user)

    def _run(self):
        min_wait_after_activity = datetime.timedelta(seconds=10)
        max_wait_after_activity = datetime.timedelta(minutes=1)

        refresh_range_by_user: dict[
            object, tuple[datetime.datetime, datetime.datetime]
        ] = dict()

        while True:
            try:
                active_user = self.queue.get(timeout=1)
            except queue.Empty:
                active_user = None
            if not self.keep_running.is_set():
                return
            now = datetime.datetime.now()
            if active_user is not None:
                if active_user in refresh_range_by_user:
                    rr_min, rr_max = refresh_range_by_user[active_user]
                    rr_min += min_wait_after_activity
                    if rr_min > rr_max:
                        rr_min = rr_max
                else:
                    rr_min = now + min_wait_after_activity
                    rr_max = now + max_wait_after_activity
                refresh_range_by_user[active_user] = rr_min, rr_max
            refresh_users = []
            for user, (rr_min, rr_max) in refresh_range_by_user.items():
                if now >= rr_min:
                    refresh_users.append(user)
            for refresh_user in refresh_users:
                refresh_range_by_user.pop(refresh_user)
                self._call_refresh_sync(refresh_user)


class ZooPeeker:
    def __init__(self, dbh: DatabaseHandler):
        self.dbh = dbh
        self.users_by_discord_id: dict[int, User] = dict()
        self.zapic_main = zooapi.ZooAPIContext()

    def get_user(self, discord_id: int):
        return self.users_by_discord_id.get(discord_id)

    def add_user(self, discord_id: int, user_name: str, user_display_name: str):
        if discord_id in self.users_by_discord_id:
            raise Exception(
                "User already added", discord_id, user_name, user_display_name
            )

        try:
            pd = self.zapic_main.get_profile_data(str(discord_id))
        except zooapi.ProfileDataUnavailableError as e:
            raise
        pds = {pd.profile_id: pd}
        unavailable_profiles = []
        for profile_zoo_id in pd.profiles:
            if profile_zoo_id in pds:
                continue
            try:
                pd = self.zapic_main.get_profile_data(f"{discord_id}_{profile_zoo_id}")
            except zooapi.ProfileDataUnavailableError as e:
                unavailable_profiles.append(profile_zoo_id)
            else:
                assert pd.profile_id == profile_zoo_id
                pds[profile_zoo_id] = pd

        with self.dbh.transaction():
            user_id = self.dbh.add_user(str(discord_id), user_name, user_display_name)

            profile_id_by_profile_zoo_id: dict[str, int] = dict()
            for pd in pds.values():
                profile_zoo_id = pd.profile_id

                profile_id = self._add_profile(user_id, profile_zoo_id, pd)

                profile_id_by_profile_zoo_id[profile_zoo_id] = profile_id

            for profile_zoo_id in unavailable_profiles:
                profile_id = self.dbh.add_profile(
                    user_id,
                    profile_zoo_id,
                    "?",
                    dict(),
                    dict(),
                )
                profile_id_by_profile_zoo_id[profile_zoo_id] = profile_id

        user = User(user_name, discord_id, user_id, profile_id_by_profile_zoo_id)
        self.users_by_discord_id[discord_id] = user

        return user

    def _pd_to_amounts(self, pd: zooapi.ZooProfileData):
        animals_amount = pd.animals.copy()
        if pd.animal_on_quest:
            animals_amount[pd.animal_on_quest] = (
                animals_amount.get(pd.animal_on_quest, 0) + 1
            )

        animals_amount_now = pd.animals

        return animals_amount, animals_amount_now

    def _add_profile(
        self, user_id: int, profile_zoo_id: str, pd: zooapi.ZooProfileData
    ):
        animals_amount, animals_amount_now = self._pd_to_amounts(pd)

        profile_id = self.dbh.add_profile(
            user_id,
            profile_zoo_id,
            pd.profile_name,
            animals_amount,
            animals_amount_now,
        )

        return profile_id

    def _update_profile(self, profile_id: int, pd: zooapi.ZooProfileData):
        animals_amount, animals_amount_now = self._pd_to_amounts(pd)

        profile_id = self.dbh.update_profile(
            profile_id,
            pd.profile_name,
            animals_amount,
            animals_amount_now,
        )

    def refresh_user_data(self, user: User):
        try:
            pd = self.zapic_main.get_profile_data(str(user.discord_id))
        except zooapi.ProfileDataUnavailableError as e:
            raise
        pds = {pd.profile_id: pd}

        updated_profile_zoo_ids = set(pd.profiles)
        known_profile_zoo_ids = set(user.profile_id_by_profile_zoo_id.keys())
        new_profile_zoo_ids = updated_profile_zoo_ids - known_profile_zoo_ids
        removed_profile_zoo_ids = known_profile_zoo_ids - updated_profile_zoo_ids
        updated_profile_id_by_profile_zoo_id = user.profile_id_by_profile_zoo_id.copy()
        with self.dbh.transaction():
            for new_profile_zoo_id in new_profile_zoo_ids:
                pd = pds.get(new_profile_zoo_id)
                if pd is None:
                    try:
                        pd = self.zapic_main.get_profile_data(
                            f"{user.discord_id}_{new_profile_zoo_id}"
                        )
                    except zooapi.ProfileDataUnavailableError as e:
                        pass
                    pds[new_profile_zoo_id] = pd
                    if pd is None:
                        continue
                profile_id = self._add_profile(user.user_id, new_profile_zoo_id, pd)
                updated_profile_id_by_profile_zoo_id[new_profile_zoo_id] = profile_id
            for removed_profile_zoo_id in removed_profile_zoo_ids:
                self.dbh.remove_profile(
                    updated_profile_id_by_profile_zoo_id[removed_profile_zoo_id]
                )
                del updated_profile_id_by_profile_zoo_id[removed_profile_zoo_id]
        user.profile_id_by_profile_zoo_id = updated_profile_id_by_profile_zoo_id

        kept_profile_zoo_ids = updated_profile_zoo_ids & known_profile_zoo_ids
        with self.dbh.transaction():
            for profile_zoo_id in kept_profile_zoo_ids:
                pd = pds.get(profile_zoo_id)
                if pd is None:
                    try:
                        pd = self.zapic_main.get_profile_data(
                            f"{user.discord_id}_{profile_zoo_id}"
                        )
                    except zooapi.ProfileDataUnavailableError as e:
                        pass
                    pds[profile_zoo_id] = pd
                    if pd is None:
                        continue
                self._update_profile(
                    user.profile_id_by_profile_zoo_id[profile_zoo_id],
                    pd,
                )

    def set_current_profile_todos(
        self,
        user: User,
        times_by_thing: dict[str, datetime.datetime],
    ):
        try:
            pd = self.zapic_main.get_profile_data(str(user.discord_id))
        except zooapi.ProfileDataUnavailableError as e:
            print("Can't set todos for", user, "because", e)
            return
        if pd.profile_id not in user.profile_id_by_profile_zoo_id:
            print(
                "Trying to set todos for unknown profile (new profile?), aborting", pd
            )
            return
        profile_id = user.profile_id_by_profile_zoo_id[pd.profile_id]
        with self.dbh.transaction():
            self.dbh.set_profile_todos(profile_id, times_by_thing)


def main():
    DRAGORN_DISCORD_SNOWFLAKE = 154239303613022209
    discord_id = DRAGORN_DISCORD_SNOWFLAKE

    with DatabaseHandler() as dbh:
        zp = ZooPeeker(dbh)
        user = zp.add_user(str(discord_id), "Dragorn421")

        ucon = dbh.get_user_con(user)

        try:
            ucon.execute("DROP TABLE zoos")
        except sqlite3.OperationalError as e:
            print(repr(e))

        from pprint import pprint

        for stmt in (
            "SELECT animal_id, amount FROM zoos",
            "SELECT animal_id, animal_emoji, amount FROM zoos JOIN animals USING(animal_id)",
            "SELECT animal_id, amount, profile_name FROM zoos JOIN profiles USING(profile_id)",
            "SELECT animal_id, animal_emoji, amount, profile_name FROM zoos JOIN animals USING(animal_id) JOIN profiles USING(profile_id)",
        ):
            print(stmt)
            cur = ucon.execute(stmt)
            print([d[0] for d in cur.description])
            res = list(cur)
            print(len(res))
            pprint(res[:5])
            print()


if __name__ == "__main__":
    main()
