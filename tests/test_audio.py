import json

import pytest

from dockit.core import audio
from dockit.core import profiles as pf

SINKS = [
    {"name": "alsa_output.pci.speaker", "description": "Ryzen HD Audio Controller Speaker", "mute": False,
     "volume": {"front-left": {"value_percent": "40%"}, "front-right": {"value_percent": "40%"}}},
    {"name": "alsa_output.usb-EPOS.analog-stereo", "description": "EPOS H3PRO Аналоговый стерео", "mute": False,
     "volume": {"mono": {"value_percent": "60%"}}},
    {"name": "alsa_output.usb-EPOS.analog-stereo.monitor", "description": "Monitor of EPOS", "mute": False},
]
SOURCES = [
    {"name": "alsa_input.pci.mic", "description": "Digital Microphone", "mute": True,
     "volume": {"mono": {"value_percent": "100%"}}},
    {"name": "alsa_input.usb-EPOS.mono", "description": "EPOS H3PRO Моно", "mute": False},
    {"name": "alsa_output.usb-EPOS.analog-stereo.monitor", "description": "Monitor of EPOS", "mute": False},
]


class FakePactl:
    def __init__(self):
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if args == ["-f", "json", "list", "sinks"]:
            return json.dumps(SINKS)
        if args == ["-f", "json", "list", "sources"]:
            return json.dumps(SOURCES)
        if args == ["get-default-sink"]:
            return "alsa_output.usb-EPOS.analog-stereo\n"
        if args == ["get-default-source"]:
            return "alsa_input.pci.mic\n"
        return ""


def test_list_skips_monitors_and_reads_state():
    devices = audio.list_devices(FakePactl())
    assert [d.description for d in devices if d.kind == "output"] == [
        "Ryzen HD Audio Controller Speaker", "EPOS H3PRO Аналоговый стерео"]
    assert len([d for d in devices if d.kind == "input"]) == 2
    epos = next(d for d in devices if "EPOS" in d.description and d.kind == "output")
    assert epos.default and epos.volume == 60
    mic = next(d for d in devices if d.kind == "input" and d.default)
    assert mic.muted and mic.volume == 100


def test_find_ignores_case():
    devices = audio.list_devices(FakePactl())
    assert audio.find(devices, "output", "epos").name == "alsa_output.usb-EPOS.analog-stereo"
    assert audio.find(devices, "output", "SPEAKER").name == "alsa_output.pci.speaker"
    assert audio.find(devices, "output", "") is None
    assert audio.find(devices, "input", "nothing") is None


def test_set_default_uses_system_name_not_user_text():
    run = FakePactl()
    device = audio.set_default("output", "speaker", run)
    assert device.name == "alsa_output.pci.speaker"
    assert run.calls[-1] == ["set-default-sink", "alsa_output.pci.speaker"]


def test_set_default_unknown_device_changes_nothing():
    run = FakePactl()
    with pytest.raises(audio.AudioError):
        audio.set_default("output", "--evil; rm", run)
    assert not any(c[0].startswith("set-") for c in run.calls)


def test_mute_and_volume():
    run = FakePactl()
    audio.set_mute("input", True, run)
    audio.set_volume("output", 50, run)
    assert run.calls == [["set-source-mute", "@DEFAULT_SOURCE@", "1"],
                         ["set-sink-volume", "@DEFAULT_SINK@", "50%"]]


@pytest.mark.parametrize("bad", [-1, 151, "50", None, True, 5.5])
def test_bad_volume_refused(bad):
    run = FakePactl()
    with pytest.raises(audio.AudioError):
        audio.set_volume("output", bad, run)
    assert run.calls == []


def test_broken_output_is_an_error_not_a_crash():
    with pytest.raises(audio.AudioError):
        audio.list_devices(lambda a: "not json")


def test_profile_audio_fields_from_file(tmp_path):
    f = tmp_path / "p.toml"
    f.write_text('[profiles.games]\noutput = "epos"\ninput = "epos"\n')
    profs, _ = pf.load(f)
    assert profs["games"].output == "epos" and profs["games"].input == "epos"
    assert profs["games"].power == "performance"  # other settings stay


def test_profile_apply_reports_missing_audio_device(monkeypatch):
    def fail(kind, query, run=None):
        raise audio.AudioError("Устройство «x» не найдено.")

    monkeypatch.setattr(audio, "set_default", fail)
    lines = pf.apply(pf.Profile("a", "A", output="x"), lambda r: {})
    assert any("не найдено" in line for line in lines)
