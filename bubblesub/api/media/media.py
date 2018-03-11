import os
import locale
import atexit
import tempfile
import fractions
from pathlib import Path

import mpv
from PyQt5 import QtCore

import bubblesub.util
from bubblesub.api.media.audio import AudioApi
from bubblesub.api.media.video import VideoApi


class MediaApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal()
    parsed = QtCore.pyqtSignal()
    current_pts_changed = QtCore.pyqtSignal()
    max_pts_changed = QtCore.pyqtSignal()
    volume_changed = QtCore.pyqtSignal()
    playback_speed_changed = QtCore.pyqtSignal()

    def __init__(self, subs_api, log_api, opt_api, args):
        super().__init__()

        self._log_api = log_api
        self._subs_api = subs_api
        self._opt_api = opt_api

        _, self._tmp_subs_path = tempfile.mkstemp(suffix='.ass')
        atexit.register(lambda: os.unlink(self._tmp_subs_path))

        self._path = None
        self._playback_speed = fractions.Fraction(1.0)
        self._volume = fractions.Fraction(100.0)
        self._current_pts = 0
        self._max_pts = 0
        self._mpv_ready = False
        self._need_subs_refresh = False

        self._subs_api.loaded.connect(self._on_subs_load)
        self._subs_api.lines.item_changed.connect(self._on_subs_change)
        self._subs_api.lines.items_removed.connect(self._on_subs_change)
        self._subs_api.lines.items_inserted.connect(self._on_subs_change)
        self._subs_api.styles.item_changed.connect(self._on_subs_change)
        self._subs_api.styles.items_removed.connect(self._on_subs_change)
        self._subs_api.styles.items_inserted.connect(self._on_subs_change)
        self._subs_api.selection_changed.connect(
            self._on_grid_selection_change)

        locale.setlocale(locale.LC_NUMERIC, 'C')
        self._mpv = mpv.Context()
        self._mpv.set_log_level('error')
        self._mpv.set_option('config', False)
        self._mpv.set_option('quiet', False)
        self._mpv.set_option('msg-level', 'all=error')
        self._mpv.set_option('osc', False)
        self._mpv.set_option('osd-bar', False)
        self._mpv.set_option('cursor-autohide', 'no')
        self._mpv.set_option('input-cursor', False)
        self._mpv.set_option('input-vo-keyboard', False)
        self._mpv.set_option('input-default-bindings', False)
        self._mpv.set_option('ytdl', False)
        self._mpv.set_option('sub-auto', False)
        self._mpv.set_option('audio-file-auto', False)
        self._mpv.set_option('vo', 'null' if args.no_video else 'opengl-cb')
        self._mpv.set_option('pause', True)
        self._mpv.set_option('idle', True)
        self._mpv.set_option('sid', False)
        self._mpv.set_option('video-sync', 'display-vdrop')
        self._mpv.set_option('keepaspect', True)
        self._mpv.set_option('hwdec', 'auto')
        self._mpv.set_option('stop-playback-on-init-failure', False)
        self._mpv.set_option('keep-open', True)

        self._mpv.observe_property('time-pos')
        self._mpv.observe_property('duration')
        self._mpv.set_wakeup_callback(self._mpv_event_handler)
        self._mpv.initialize()

        self.video = VideoApi(self, log_api)
        self.audio = AudioApi(self, log_api)

        self._timer = QtCore.QTimer(
            self, interval=opt_api.general['video']['subs_sync_interval'])
        self._timer.timeout.connect(self._refresh_subs_if_needed)

    def start(self):
        self._timer.start()

    def unload(self):
        self._path = None
        self.loaded.emit()
        self._reload_video()

    def load(self, path):
        assert path
        self._path = Path(path)
        if str(self._subs_api.remembered_video_path) != str(self._path):
            self._subs_api.remembered_video_path = self._path
        self._reload_video()
        self.loaded.emit()

    def seek(self, pts, precise=True):
        if not self._mpv_ready:
            return
        self._set_end(None)  # mpv refuses to seek beyond --end
        pts = max(0, pts)
        pts = self.video.align_pts_to_next_frame(pts)
        if pts != self.current_pts:
            self._mpv.command(
                'seek',
                bubblesub.util.ms_to_str(pts),
                'absolute+exact' if precise else 'absolute')

    def step_frame_forward(self):
        if not self._mpv_ready:
            return
        self._set_end(None)  # mpv refuses to seek beyond --end
        self._mpv.command('frame-step')

    def step_frame_backward(self):
        if not self._mpv_ready:
            return
        self._set_end(None)  # mpv refuses to seek beyond --end
        self._mpv.command('frame-back-step')

    def play(self, start, end):
        self._play(start, end)

    def unpause(self):
        self._play(None, None)

    def pause(self):
        self._mpv.set_property('pause', True)

    @property
    def playback_speed(self):
        return self._playback_speed

    @playback_speed.setter
    def playback_speed(self, value):
        self._playback_speed = value
        self._mpv.set_property('speed', float(self._playback_speed))
        self.playback_speed_changed.emit()

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = value
        self._mpv.set_property('volume', float(self._volume))
        self.volume_changed.emit()

    @property
    def current_pts(self):
        return self._current_pts

    @property
    def max_pts(self):
        return self._max_pts

    @property
    def is_paused(self):
        if not self._mpv_ready:
            return True
        return self._mpv.get_property('pause')

    @property
    def path(self):
        return self._path

    @property
    def is_loaded(self):
        return self._path is not None

    def _play(self, start, end):
        if not self._mpv_ready:
            return
        if start is not None:
            self.seek(start)
        self._set_end(end)
        self._mpv.set_property('pause', False)

    def _set_end(self, end):
        if end is None:
            # XXX: mpv doesn't accept None nor "" so we use max pts
            end = self._mpv.get_property('duration') * 1000
        end = max(0, end)
        self._mpv.set_option('end', bubblesub.util.ms_to_str(end))

    def _mpv_unloaded(self):
        self._mpv_ready = False
        self.parsed.emit()

    def _mpv_loaded(self):
        self._mpv_ready = True
        self._mpv.command('sub_add', str(self._tmp_subs_path))
        self._refresh_subs()
        self.parsed.emit()

    def _on_subs_load(self):
        if self._subs_api.remembered_video_path:
            self.load(self._subs_api.remembered_video_path)
        else:
            self.unload()
        self._on_subs_change()

    def _on_subs_change(self):
        self._need_subs_refresh = True

    def _reload_video(self):
        self._subs_api.save_ass(self._tmp_subs_path)
        self._mpv_ready = False
        self._mpv.set_property('pause', True)
        if not self.path or not self.path.exists():
            self._mpv.command('loadfile', '')
        else:
            self._mpv.command('loadfile', str(self.path))

    def _refresh_subs_if_needed(self):
        if self._need_subs_refresh:
            self._refresh_subs()

    def _refresh_subs(self):
        if not self._mpv_ready:
            return
        self._subs_api.save_ass(self._tmp_subs_path)
        if self._mpv.get_property('sub'):
            self._mpv.command('sub_reload')
            self._need_subs_refresh = False

    def _on_grid_selection_change(self, rows, _changed):
        if len(rows) == 1:
            self.pause()
            self.seek(self._subs_api.lines[rows[0]].start)

    def _mpv_event_handler(self):
        while self._mpv:
            event = self._mpv.wait_event(.01)
            if event.id in {mpv.Events.none, mpv.Events.shutdown}:
                break
            elif event.id == mpv.Events.end_file:
                self._mpv_unloaded()
            elif event.id == mpv.Events.file_loaded:
                self._mpv_loaded()
            elif event.id == mpv.Events.log_message:
                event_log = event.data
                self._log_api.debug(
                    'video/{}: {}'.format(
                        event_log.prefix,
                        event_log.text.strip()))
            elif event.id == mpv.Events.property_change:
                event_prop = event.data
                if event_prop.name == 'time-pos':
                    self._current_pts = event_prop.data * 1000
                    self.current_pts_changed.emit()
                elif event_prop.name == 'duration':
                    self._max_pts = event_prop.data * 1000
                    self.max_pts_changed.emit()