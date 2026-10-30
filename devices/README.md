# Device database

One small text file per device, so a new device can be added without touching Python code.
Devices are matched by hardware ID (USB `vendor:product`, or the model name from BIOS for
laptops), not by typed names, so upper or lower case does not matter.

```
devices/
  laptops/     matched by BIOS model name (dmi_product)
  mice/        matched by USB ID
  headsets/
  cameras/
  keyboards/
  bluetooth/
```

## Format (TOML)

```toml
name = "Example mouse"       # shown to the user
kind = "mouse"               # laptop, mouse, headset, camera, keyboard, bluetooth
usb_id = "0000:0000"         # from `lsusb`, the ID after "ID" (not for laptops)
status = "detected"          # untested / detected / partial / full
features = ["detect"]        # what is known to work
notes = "Short plain-text remark."
```

For a laptop use `dmi_product` instead of `usb_id`. It is the value printed as `model`
by `dockit report`.

## Add your device

1. Run `lsusb` and find your device. The ID looks like `379a:3608`.
2. Copy an existing file in the matching folder and change the fields.
3. Open a pull request, or send the `dockit report` output in an issue and we will add it.

Do not put serial numbers or personal data into these files.
