# Music Replacer MVP

Первый MVP: проверяет OGG/Vorbis и патчит одну запись STRQ/STQ. ARC пока не
перепаковывается: пользователь вручную заменяет извлечённый STQ в `title.arc`.
Исходный ARC не трогается.

Подтверждено на игре: STQ действительно управляет физическим путём файла.
Движок разрешает target name относительно `nativePC\\sound\\stream\\` и
сам добавляет расширение `.sngw`. Поэтому replacement устанавливается так:

```text
nativePC\\sound\\stream\\DDDA_AI_Overhaul\\music\\title\\tittleddn_a.sngw
```

Исходный OGG/Vorbis можно использовать как содержимое, но файл обязан иметь
расширение `.sngw`. То есть для текущего теста важны одновременно Vorbis-
данные и игровой контейнерный суффикс `.sngw`; отдельный CreateFile-hook не
нужен.

## Первый тест титла

```bash
python3 patch_stq.py \
  ../builds/84.98/resources/extracted_assets/game_main/title/sound/stream/bgm/Tittle_bgm.stq \
  /path/to/tittleddn_a.ogg \
  --out /tmp/Tittle_bgm.patched.stq
```

По умолчанию:

- источник: `bgm\\wave2\\Tittle_DDN`;
- target name: `DDDA_AI_Overhaul\\music\\title\\tittleddn_a`;
- replacement должен быть Vorbis, 6 каналов, 48000 Hz;
- loop: от sample 0 до конца replacement;
- добавляется новая строка в string blob, остальные байты STQ сохраняются;
- создаются `.report.json` с исходными/новыми полями и SHA-256.

Для one-shot:

```bash
--loop none
```

Для ручных loop points:

```bash
--loop full --loop-in 2734966 --loop-out 4078967
```

## Простой GUI

Запустите `run_gui.bat` двойным кликом. В окне выберите:

1. извлечённый `Tittle_bgm.stq`;
2. replacement `.ogg` или `.sngw`;
3. папку результата;
4. режим loop.

GUI автоматически создаст patched STQ, скопирует audio как `.sngw` в
`nativePC\\sound\\stream\\DDDA_AI_Overhaul\\music\\title\\` и сохранит
`report.json`. ARC пока остаётся ручным шагом.

## Важное ограничение MVP

Сейчас патчируется только извлечённый STQ. После проверки результата его нужно
вручную вернуть в `title.arc` и протестировать. ARC reader/writer добавляется
после подтверждения, что изменение `namePtr` действительно перенаправляет
движок на новый путь без CreateFile-хука.
