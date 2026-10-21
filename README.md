# Business English Text-to-Speech

Локальный генератор аудио-диалогов для курса Business English (Chemical Sales).
Kokoro TTS · Python · CUDA. После установки зависимостей и загрузки модели генерация выполняется локально; наличие подходящего GPU зависит от конфигурации.

---

## Структура проекта

```
text-to-speech/
├── main.py              ← главное приложение
├── install.bat          ← установка зависимостей
├── run.bat              ← быстрый запуск
├── dialogues\
│   └── library.json     ← библиотека готовых диалогов (все 6 модулей)
└── README.md
```

---

## Установка

1. **ffmpeg** → https://www.gyan.dev/ffmpeg/builds/ → распакуй в `C:\ffmpeg` → добавь `C:\ffmpeg\bin` в PATH
2. Запусти `install.bat`
3. Запусти `run.bat` или `python main.py`

---

## Библиотека диалогов

В `dialogues/library.json` находятся примеры учебных диалогов:

| Модуль | Темы |
|--------|------|
| M1 — Professional Communication | Self-intro, company structure, diplomacy, small talk, interview |
| M3 — Sales & Negotiation | Price negotiation, Incoterms, payment terms, objections |
| M4 — Reporting & Numbers | Q3 results presentation, KPIs, variance analysis |
| M5 — Logistics & Claims | Quality claims, delivery delays, complaint handling |
| M6 — Chemical Industry | Technical specs, SDS, quality deviation, QC |

---

## Формат своего диалога

```
[Имя1]: Текст реплики
[Имя2]: Ответная реплика
[Имя1]: Продолжение
```

До 4 персонажей. Каждому назначается свой голос.

---

## Как добавить свой диалог в библиотеку

Открой `dialogues/library.json` и добавь в нужный модуль:

```json
{
  "title": "Название диалога",
  "speakers": ["Имя1", "Имя2"],
  "text": "[Имя1]: ...\n[Имя2]: ..."
}
```

---

## Голоса (11 штук)

| Голос | Акцент | Пол |
|-------|--------|-----|
| am_adam | 🇺🇸 USA | муж |
| am_michael | 🇺🇸 USA | муж |
| af_heart | 🇺🇸 USA | жен |
| af_bella | 🇺🇸 USA | жен |
| af_sarah | 🇺🇸 USA | жен |
| bm_george | 🇬🇧 UK | муж |
| bm_lewis | 🇬🇧 UK | муж |
| bf_emma | 🇬🇧 UK | жен |
| bf_isabella | 🇬🇧 UK | жен |
