# SPDX-FileCopyrightText: 2024 Dragorn421
# SPDX-License-Identifier: CC0-1.0

import json
import enum
import dataclasses

import requests


def get_profile_view_url(id: str):
    return "https://gdcolon.com/zoo/" + id


def get_profile_api_url(id: str):
    return "https://gdcolon.com/zoo/api/profile/" + id


class ZooAnimal:
    animal_name: str  # "Bat"
    emoji: str  # "🦇"
    is_rare: bool

    def __str__(self) -> str:
        return self.emoji

    def __repr__(self) -> str:
        return f"<{self.emoji}>"


class ZooAnimalCommon(ZooAnimal, enum.Enum):
    BAT = ("Bat", "🦇")
    BEAR = ("Bear", "🐻")
    BEAVER = ("Beaver", "🦫")
    BEETLE = ("Beetle", "🪲")
    CAMEL = ("Camel", "🐪")
    CAT = ("Cat", "🐱")
    CATERPILLAR = ("Caterpillar", "🐛")
    CHICK = ("Chick", "🐥")
    CHICKEN = ("Chicken", "🐔")
    COW = ("Cow", "🐄")
    CRAB = ("Crab", "🦀")
    CRICKET = ("Cricket", "🦗")
    CROCODILE = ("Crocodile", "🐊")
    DINOSAUR = ("Dinosaur", "🦕")
    DOG = ("Dog", "🐶")
    DOVE = ("Dove", "🕊️")
    DUCK = ("Duck", "🦆")
    ELEPHANT = ("Elephant", "🐘")
    FISH = ("Fish", "🐟")
    FLY = ("Fly", "🪰")
    FOX = ("Fox", "🦊")
    FROG = ("Frog", "🐸")
    GIRAFFE = ("Giraffe", "🦒")
    GORILLA = ("Gorilla", "🦍")
    HAMSTER = ("Hamster", "🐹")
    HEDGEHOG = ("Hedgehog", "🦔")
    HIPPO = ("Hippo", "🦛")
    HORSE = ("Horse", "🐴")
    KOALA = ("Koala", "🐨")
    LEOPARD = ("Leopard", "🐆")
    LIZARD = ("Lizard", "🦎")
    MOUSE = ("Mouse", "🐭")
    OX = ("Ox", "🐂")
    PARROT = ("Parrot", "🦜")
    PENGUIN = ("Penguin", "🐧")
    PIG = ("Pig", "🐷")
    RABBIT = ("Rabbit", "🐰")
    SEAL = ("Seal", "🦭")
    SHEEP = ("Sheep", "🐑")
    SHRIMP = ("Shrimp", "🦐")
    SKUNK = ("Skunk", "🦨")
    SLOTH = ("Sloth", "🦥")
    SNAIL = ("Snail", "🐌")
    SNOWMAN = ("Snowman", "⛄")
    SPIDER = ("Spider", "🕷️")
    SQUID = ("Squid", "🦑")
    TURKEY = ("Turkey", "🦃")
    WHALE = ("Whale", "🐳")
    WORM = ("Worm", "🪱")
    ZEBRA = ("Zebra", "🦓")

    def __init__(self, animal_name: str, emoji: str):
        self.animal_name = animal_name
        self.emoji = emoji
        self.is_rare = False


class ZooAnimalRare(ZooAnimal, enum.Enum):
    BACTRIAN_CAMEL = ("Bactrian Camel", "🐫", ZooAnimalCommon.CAMEL)
    BADGER = ("Badger", "🦡", ZooAnimalCommon.SKUNK)
    BEE = ("Bee", "🐝", ZooAnimalCommon.SNAIL)
    BIRD = ("Bird", "🐦", ZooAnimalCommon.CHICK)
    BISON = ("Bison", "🦬", ZooAnimalCommon.OX)
    BOAR = ("Boar", "🐗", ZooAnimalCommon.PIG)
    BUNNY = ("Bunny", "🐇", ZooAnimalCommon.RABBIT)
    BUTTERFLY = ("Butterfly", "🦋", ZooAnimalCommon.CATERPILLAR)
    CHIPMUNK = ("Chipmunk", "🐿️", ZooAnimalCommon.HAMSTER)
    COCKROACH = ("Cockroach", "🪳", ZooAnimalCommon.CRICKET)
    DEER = ("Deer", "🦌", ZooAnimalCommon.HEDGEHOG)
    DODO = ("Dodo", "🦤", ZooAnimalCommon.TURKEY)
    DOLPHIN = ("Dolphin", "🐬", ZooAnimalCommon.SEAL)
    DRAGON = ("Dragon", "🐲", ZooAnimalCommon.LIZARD)
    EAGLE = ("Eagle", "🦅", ZooAnimalCommon.DOVE)
    FLAMINGO = ("Flamingo", "🦩", ZooAnimalCommon.SHRIMP)
    GOAT = ("Goat", "🐐", ZooAnimalCommon.COW)
    KANGAROO = ("Kangaroo", "🦘", ZooAnimalCommon.GIRAFFE)
    LADYBUG = ("Ladybug", "🐞", ZooAnimalCommon.BEETLE)
    LION = ("Lion", "🦁", ZooAnimalCommon.LEOPARD)
    LLAMA = ("Llama", "🦙", ZooAnimalCommon.ZEBRA)
    LOBSTER = ("Lobster", "🦞", ZooAnimalCommon.CRAB)
    MAMMOTH = ("Mammoth", "🦣", ZooAnimalCommon.ELEPHANT)
    MONKEY = ("Monkey", "🐒", ZooAnimalCommon.SLOTH)
    MOSQUITO = ("Mosquito", "🦟", ZooAnimalCommon.FLY)
    OCTOPUS = ("Octopus", "🐙", ZooAnimalCommon.SQUID)
    ORANGUTAN = ("Orangutan", "🦧", ZooAnimalCommon.GORILLA)
    OTTER = ("Otter", "🦦", ZooAnimalCommon.BEAVER)
    OWL = ("Owl", "🦉", ZooAnimalCommon.BAT)
    PANDA = ("Panda", "🐼", ZooAnimalCommon.BEAR)
    PEACOCK = ("Peacock", "🦚", ZooAnimalCommon.PARROT)
    POLAR_BEAR = ("Polar Bear", "🐻‍❄️", ZooAnimalCommon.PENGUIN)
    POODLE = ("Poodle", "🐩", ZooAnimalCommon.DOG)
    PUFFERFISH = ("Pufferfish", "🐡", ZooAnimalCommon.CROCODILE)
    RACCOON = ("Raccoon", "🦝", ZooAnimalCommon.KOALA)
    RAM = ("Ram", "🐏", ZooAnimalCommon.SHEEP)
    RAT = ("Rat", "🐀", ZooAnimalCommon.MOUSE)
    RHINO = ("Rhino", "🦏", ZooAnimalCommon.HIPPO)
    ROOSTER = ("Rooster", "🐓", ZooAnimalCommon.CHICKEN)
    SCORPION = ("Scorpion", "🦂", ZooAnimalCommon.SPIDER)
    SHARK = ("Shark", "🦈", ZooAnimalCommon.WHALE)
    SNAKE = ("Snake", "🐍", ZooAnimalCommon.WORM)
    SNOWIER_MAN = ("Snowier Man", "☃️", ZooAnimalCommon.SNOWMAN)
    SWAN = ("Swan", "🦢", ZooAnimalCommon.DUCK)
    T_REX = ("T-Rex", "🦖", ZooAnimalCommon.DINOSAUR)
    TIGER = ("Tiger", "🐯", ZooAnimalCommon.CAT)
    TROPICAL_FISH = ("Tropical Fish", "🐠", ZooAnimalCommon.FISH)
    TURTLE = ("Turtle", "🐢", ZooAnimalCommon.FROG)
    UNICORN = ("Unicorn", "🦄", ZooAnimalCommon.HORSE)
    WOLF = ("Wolf", "🐺", ZooAnimalCommon.FOX)

    def __init__(self, animal_name: str, emoji: str, animal_common: ZooAnimalCommon):
        self.animal_name = animal_name
        self.emoji = emoji
        self.animal_common = animal_common
        self.is_rare = True


ZooAnimalCommon.by_animal_name = {a.animal_name: a for a in ZooAnimalCommon}
ZooAnimalRare.by_animal_name = {a.animal_name: a for a in ZooAnimalRare}
ZooAnimal.by_animal_name = ZooAnimalCommon.by_animal_name | ZooAnimalRare.by_animal_name


@dataclasses.dataclass
class ZooProfileData:
    data_str: str = dataclasses.field(repr=False)
    """raw json"""
    data: object = dataclasses.field(repr=False)
    """parsed json"""
    profiles: list[str]
    """["chicken", "whale", "sheep", "crocodile"]"""
    profile_full_id: str
    """ "123456789012345678_whale" """
    profile_id: str
    """ "whale" """
    profile_name: str
    """ "Someone's Zoo Name" """
    animals: dict[ZooAnimal, int]
    """Animal keys may be missing. Values may be 0. Any animal on quest not included in counts."""
    animal_on_quest: ZooAnimalRare | None


class ProfileDataUnavailableError(Exception):
    def __init__(self, error_id: str, error_name: str, error_msg: str):
        super().__init__(f"{error_name} ({error_id}): {error_msg}")
        self.error_id = error_id
        self.error_name = error_name
        self.error_msg = error_msg


class ZooAPIContext:
    def __init__(self):
        self.requests_session = requests.Session()

    def get_profile_data(self, id: str):
        assert isinstance(id, str)

        url = get_profile_api_url(id)

        res = self.requests_session.get(url)
        res: requests.Response
        if res.status_code != requests.codes.OK:
            raise Exception("not OK", res.status_code, res)
        data_str = res.text

        try:
            data = json.loads(data_str)
        except:
            print(data_str)
            raise
        if "error" in data:
            """
            Examples:

            {
                "name": "Cursed profile!",
                "msg": "This profile has a <b>curse of invisibility</b> and cannot be viewed right now.",
                "login": true,
                "invalid": true,
                "error": "invisible"
            }

            {
                "name": "Invalid profile!",
                "msg": "It doesn't look like this profile exists. Oh well!",
                "invalid": true,
                "error": "invalidProfile"
            }
            """
            raise ProfileDataUnavailableError(
                data["error"],
                data["name"],
                data["msg"],
            )

        try:
            return ZooProfileData(
                data_str=data_str,
                data=data,
                profiles=data["profiles"],
                profile_full_id=data["id"],
                profile_id=data["profileID"],
                profile_name=data["name"],
                animals={
                    ZooAnimal.by_animal_name[data_animal["name"]]: data_animal["amount"]
                    for data_animal in data["animals"]
                },
                animal_on_quest=(
                    ZooAnimalRare.by_animal_name[data["quest"]["animal"]]
                    if (
                        # data["quest"] json is null if no quest is on
                        data.get("quest")
                        is not None
                    )
                    else None
                ),
            )
        except Exception as e:
            e.add_note(f"{url=!r}")
            e.add_note(f"{data=!r}")
            raise


def main():
    zapic = ZooAPIContext()

    import time

    import botconf

    t1 = time.time()
    for _ in range(10):
        print(zapic.get_profile_data(str(botconf.dragorn421_user_id)))
    t2 = time.time()
    print(t2 - t1)


if __name__ == "__main__":
    main()
