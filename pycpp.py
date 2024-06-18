# SPDX-FileCopyrightText: 2024 Dragorn421
# SPDX-License-Identifier: CC0-1.0

import io

import pcpp


class ForbiddenUsage(Exception):
    pass


class MyCPP(pcpp.Preprocessor):
    def __init__(self):
        super().__init__()
        self.line_directive = None

    def on_directive_handle(self, directive, toks, ifpassthru, precedingtoks):
        assert isinstance(directive, pcpp.parser.LexToken)

        directive_name = directive.value

        if directive_name == "include":
            raise ForbiddenUsage("#include is forbidden")

        if directive_name not in {
            "define",
            "undef",
            "ifdef",
            "ifndef",
            "if",
            "elif",
            "else",
            "endif",
        }:
            raise ForbiddenUsage("Unknown directive", directive_name)

        return super().on_directive_handle(directive, toks, ifpassthru, precedingtoks)

    def on_file_open(self, is_system_include, includepath):
        raise Exception("#include yeeted")

    def on_include_not_found(
        self, is_malformed, is_system_include, curdir, includepath
    ):
        raise Exception("#include yeeted")


def my_preprocess(text: str):
    mycpp = MyCPP()
    mycpp.parse(text)
    out = io.StringIO()
    mycpp.write(out)
    return out.getvalue()


def main():
    mycpp = MyCPP()
    mycpp.parse(
        """#define Joined zoos join animals using(animal_id)
SELECT * FROM Joined
"""
        + """#define k1 nopelol
#define B(n) z # n k ## n
B(1)

#define Score CASE is_rare WHEN TRUE THEN 5 * amount ELSE amount END
"""
    )
    out = io.StringIO()
    mycpp.write(out)
    print(out.getvalue())


if __name__ == "__main__":
    main()
