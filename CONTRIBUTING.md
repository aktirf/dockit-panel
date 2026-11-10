# Contributing to DOCKIT

Thanks for helping! DOCKIT is a Linux laptop control panel (GPL-3.0-or-later).
Русская версия ниже.

## Quick start
```bash
git clone https://github.com/aktirf/dockit-panel
cd dockit-panel
python -m venv .venv && source .venv/bin/activate
pip install -e . pytest
python -m pytest -q          # should pass without any special hardware
dockit scan                  # read-only scan of your laptop
```
Fork the repo (or ask for write access), create a branch, open a pull request into `main`.
Please read [AGENTS.md](AGENTS.md): it describes the code layout and our guidelines (they are
useful for humans too). If your AI tool does not load it automatically, ask it to read that file first.

## Good first contributions
- Add your device to the database in `devices/` (one small text file, see `devices/README.md`).
  Run `scripts/probe.sh` and attach `~/dockit-probe.txt` to an issue for a new laptop.
- Support for another desktop or compositor in `src/dockit/core/display.py`.
- Interface language (English UI) and keyboard layout settings.
- A test for any parser that has none yet.

## Rules in short
- Core code does not import Qt; the window only shows what `viewmodel.py` gives it.
- Anything that changes the system goes through the root service with confirmation.
- Every parser or rule gets a unit test using sample text.
- One topic per pull request. Describe what you changed and on which hardware/desktop you tried it.
- We cannot test your GUI changes for you: attach a screenshot or log.

---

## Как помочь (по-русски)
1. Сделай форк репозитория или попроси доступ на запись.
2. Создай ветку, внеси правки, запусти `python -m pytest -q` (все тесты должны проходить).
3. Открой pull request в ветку `main` и опиши, что изменил и на каком ноутбуке и окружении проверил.
4. Если используешь Claude или другого ИИ-помощника, пусть он сначала прочитает `AGENTS.md` (если инструмент не подхватывает его сам, попроси прочитать его явно).

Хорошие первые задачи: добавить своё устройство в `devices/`, поддержку ещё одного окружения
рабочего стола, английский язык интерфейса, настройки раскладки клавиатуры, тесты.
