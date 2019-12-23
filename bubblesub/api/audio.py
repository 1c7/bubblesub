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

"""Audio stream API."""

import typing as T
from pathlib import Path

from bubblesub.api.audio_stream import AudioStream
from bubblesub.api.base_streams_api import BaseStreamsApi, TStream
from bubblesub.api.log import LogApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.threading import ThreadingApi

if T.TYPE_CHECKING:
    AudioApiBaseClass = BaseStreamsApi[AudioStream]
else:
    AudioApiBaseClass = BaseStreamsApi


class AudioApi(AudioApiBaseClass):
    """Manages audio streams."""

    def __init__(
        self,
        threading_api: ThreadingApi,
        log_api: LogApi,
        subs_api: SubtitlesApi,
    ) -> None:
        """Initialize self.

        :param threading_api: threading API
        :param log_api: logging API
        :param subs_api: subtitles API
        """
        super().__init__()
        self._threading_api = threading_api
        self._log_api = log_api
        self._subs_api = subs_api

    def _stream_loaded(self, stream: AudioStream) -> None:
        super()._stream_loaded(stream)
        self._subs_api.remember_audio_path_if_needed(stream.path)

    def _create_stream(self, path: Path) -> TStream:
        return AudioStream(self._threading_api, self._log_api, path)
