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

import argparse

import bubblesub.api
from bubblesub.api.cmd import BaseCommand
from bubblesub.cmd.common import BooleanOperation


class MuteCommand(BaseCommand):
    names = ['mute']
    help_text = 'Mutes or unmutes the video audio.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        self.api.media.mute = self.args.operation.apply(self.api.media.mute)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'operation',
            help='whether to mute the audio',
            type=BooleanOperation
        )


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    cmd_api.register_core_command(MuteCommand)
