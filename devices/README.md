# Device database

One small text file per device, so new devices can be added without touching Python code.
Devices are matched by hardware ID (for example USB `vendor:product`), not by typed names,
so upper or lower case does not matter.

Planned layout:

```
devices/
  laptops/   by DMI product name
  mice/      by USB ID
  headsets/  by USB ID
```

Draft format (TOML, subject to change):

```toml
name = "Example mouse"
usb_id = "0000:0000"      # replace with the real ID from `lsusb`
kind = "mouse"
features = ["battery", "dpi"]
status = "untested"       # untested / partial / full
```
