#!/usr/bin/env python3
"""Add i18n keys for new GPTHub agents to all locale files."""
import json
import glob
import os

new_keys = {
    "Vision": "Vision",
    "Analyses images, screenshots and photos \u2014 describe or ask questions about what you see.": "Analyses images, screenshots and photos \u2014 describe or ask questions about what you see.",
    "Web Search": "Web Search",
    "Searches the web and gives you up-to-date information with cited sources.": "Searches the web and gives you up-to-date information with cited sources.",
    "Deep Research": "Deep Research",
    "Conducts multi-step research across multiple sources and delivers a structured report.": "Conducts multi-step research across multiple sources and delivers a structured report.",
}

ru_overrides = {
    "Vision": "Vision",
    "Analyses images, screenshots and photos \u2014 describe or ask questions about what you see.": "\u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0435\u0442 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f, \u0441\u043a\u0440\u0438\u043d\u0448\u043e\u0442\u044b \u0438 \u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0438\u0438 \u2014 \u043e\u043f\u0438\u0448\u0438\u0442\u0435 \u0438\u043b\u0438 \u0437\u0430\u0434\u0430\u0439\u0442\u0435 \u0432\u043e\u043f\u0440\u043e\u0441.",
    "Web Search": "Web Search",
    "Searches the web and gives you up-to-date information with cited sources.": "\u0418\u0449\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u044e \u0432 \u0441\u0435\u0442\u0438 \u0438 \u043f\u0440\u0435\u0434\u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442 \u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435 \u0441\u043e \u0441\u0441\u044b\u043b\u043a\u0430\u043c\u0438.",
    "Deep Research": "Deep Research",
    "Conducts multi-step research across multiple sources and delivers a structured report.": "\u041f\u0440\u043e\u0432\u043e\u0434\u0438\u0442 \u043c\u043d\u043e\u0433\u043e\u044d\u0442\u0430\u043f\u043d\u043e\u0435 \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435 \u043f\u043e \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u0438\u043c \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u0430\u043c \u0438 \u0441\u043e\u0437\u0434\u0430\u0451\u0442 \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u043e\u0442\u0447\u0451\u0442.",
}

script_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(script_dir)
locale_files = sorted(glob.glob(os.path.join(root, "src/lib/i18n/locales/*/translation.json")))
updated = 0

for filepath in locale_files:
    locale = os.path.basename(os.path.dirname(filepath))
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    changed = False
    for key, default_val in new_keys.items():
        if key not in data:
            if locale.startswith('ru'):
                data[key] = ru_overrides.get(key, default_val)
            else:
                data[key] = default_val
            changed = True

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent='\t')
            f.write('\n')
        updated += 1

print(f"Updated {updated} / {len(locale_files)} locale files")
