# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Various ASS utilities."""

import typing as T
from functools import lru_cache

import ass_tag_parser
import regex

from bubblesub.spell_check import BaseSpellChecker


def escape_ass_tag(text: str) -> str:
    """Escape text so that it doesn't get treated as ASS tags.

    :param text: text to escape
    :return: escaped text
    """
    return text.replace("\\", r"\\").replace("{", r"\[").replace("}", r"\]")


def unescape_ass_tag(text: str) -> str:
    """Do the reverse operation to escape_ass_tag().

    :param text: text to unescape
    :return: unescaped text
    """
    return text.replace(r"\\", "\\").replace(r"\[", "{").replace(r"\]", "}")


@lru_cache(maxsize=5000)
def ass_to_plaintext(text: str) -> str:
    """Strip ASS tags from an ASS line.

    :param text: input ASS line
    :return: plain text
    """
    try:
        ass_line = ass_tag_parser.parse_ass(text)
    except ass_tag_parser.ParseError:
        ret = str(regex.sub("{[^}]*}", "", text))
    else:
        ret = ""
        for item in ass_line:
            if isinstance(item, ass_tag_parser.AssText):
                ret += item.text
    return ret.replace("\\h", " ").replace("\\n", " ").replace("\\N", "\n")


@lru_cache(maxsize=5000)
def character_count(text: str) -> int:
    """Count how many characters an ASS line contains.

    Doesn't take into account effects such as text invisibility etc.

    :param text: input ASS line
    :return: number of characters
    """
    return len(
        regex.sub(r"\W+", "", ass_to_plaintext(text), flags=regex.I | regex.U)
    )


def iter_words_ass_line(text: str) -> T.Iterable[T.Match[str]]:
    """Iterate over words within an ASS line.

    Doesn't take into account effects such as text invisibility etc.

    :param text: input ASS line
    :return: iterator over regex matches
    """
    text = regex.sub(
        r"\\[Nnh]", "  ", text  # two spaces to preserve match positions
    )

    return T.cast(
        T.Iterable[T.Match[str]],
        regex.finditer(
            r"[\p{L}\p{S}\p{N}][\p{L}\p{S}\p{N}\p{P}]*\p{L}|\p{L}", text
        ),
    )


@lru_cache(maxsize=500)
def spell_check_ass_line(
    spell_checker: BaseSpellChecker, text: str
) -> T.Iterable[T.Tuple[int, int, str]]:
    """Iterate over badly spelled words within an ASS line.

    Doesn't take into account effects such as text invisibility etc.

    :param spell_checker: spell checker to validate the words with
    :param text: input ASS line
    :return: iterator over tuples with start, end and text
    """
    try:
        ass_line = ass_tag_parser.parse_ass(text)
    except ass_tag_parser.ParseError:
        return []

    results: T.List[T.Tuple[int, int, str]] = []

    for item in ass_line:
        if isinstance(item, ass_tag_parser.AssText):
            for match in iter_words_ass_line(item.text):
                word = match.group(0)
                if not spell_checker.check(word):
                    results.append(
                        (
                            item.meta.start + match.start(),
                            item.meta.start + match.end(),
                            word,
                        )
                    )

    return results
