from pathlib import Path

from dockit.core.usb import list_usb
from dockit.peripherals.database import find_by_usb, find_laptop, load_database
from dockit.peripherals.scan import scan_peripherals


def _usb(base: Path, name: str, vendor: str, product: str, title: str = ""):
    d = base / name
    d.mkdir(parents=True)
    (d / "idVendor").write_text(vendor + "\n")
    (d / "idProduct").write_text(product + "\n")
    if title:
        (d / "product").write_text(title + "\n")


def test_list_usb_skips_root_hubs_and_interfaces(tmp_path):
    base = tmp_path / "usb"
    _usb(base, "usb1", "1d6b", "0002", "xHCI Host Controller")  # root hub
    _usb(base, "3-1", "3277", "00B2", "GIGABYTE FHD CAMERA")
    (base / "3-1:1.0").mkdir()                                  # interface
    devices = list_usb(base)
    assert [d.usb_id for d in devices] == ["3277:00b2"]
    assert devices[0].port == "3-1"


def test_known_and_unknown_devices(tmp_path):
    base = tmp_path / "usb"
    _usb(base, "3-1", "3277", "00b2", "GIGABYTE FHD CAMERA")
    _usb(base, "9-9", "1234", "abcd", "Mystery Gadget")
    db = tmp_path / "devices"
    db.mkdir()
    # upper case in the file on purpose: matching must ignore case
    (db / "cam.toml").write_text(
        'name = "Test camera"\nkind = "camera"\nusb_id = "3277:00B2"\nstatus = "partial"\n'
    )
    items = scan_peripherals(list_usb(base), load_database([db]))
    by_id = {i.usb_id: i for i in items}
    assert by_id["3277:00b2"].known and by_id["3277:00b2"].name == "Test camera"
    assert not by_id["1234:abcd"].known and by_id["1234:abcd"].name == "Mystery Gadget"
    assert items[0].known  # known devices come first


def test_broken_database_file_is_ignored(tmp_path):
    (tmp_path / "bad.toml").write_text("this is = = not toml")
    (tmp_path / "noname.toml").write_text('kind = "mouse"\n')
    assert load_database([tmp_path]) == []


def test_shipped_database_has_the_first_devices():
    entries = load_database()
    assert find_by_usb(entries, "379A:3608").kind == "mouse"
    assert find_by_usb(entries, "1395:0101").kind == "headset"
    assert find_by_usb(entries, "3277:00b2").kind == "camera"
    laptop = find_laptop(entries, "gigabyte  gaming a16 3vh")
    assert laptop is not None and laptop.status == "partial"


def test_device_with_several_usb_ids(tmp_path):
    (tmp_path / "m.toml").write_text(
        'name = "Mouse"\nkind = "mouse"\nusb_id = "379a:3608"\nusb_ids = ["379A:3607"]\n'
    )
    entries = load_database([tmp_path])
    assert find_by_usb(entries, "379a:3607").name == "Mouse"
    assert find_by_usb(entries, "379a:3608").name == "Mouse"
    assert find_by_usb(entries, "379a:0000") is None
