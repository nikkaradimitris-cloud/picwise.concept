"""The checks of every product on its shop's own site (`docs/PICWISE_CHECKS_RULES.md`).

Owner, 2026-11-21: «Ποιότητα πάνω από ποσότητα. Όποιο προϊόν δεν περνά τον έλεγχο
κόβεται, και όποιο κατάστημα δεν δέχεται το bot βγαίνει ολόκληρο. Τη θέση τους μέσα στο
όριο των 12.000 την παίρνουν προϊόντα που πέρασαν τον έλεγχο»; and, the same evening, his
six answers (the rules' section 2.2).

What is here is code without a network (the rules' section 14): what a shop's answer
means (`verdicts`), the brakes (`brakes`), a product page read (`page_reader`), and what
is remembered from night to night and what the preparation reads (`ledger`). The bot that
asks the shops (`deployment/bot/shop_checks_bot.py`) only fetches; the preparation reads
the night's decisions through `picwise_providers.checks_applied`, behind the one switch of
the rules' section 7.7 (`data/checks_switch.json`).
"""
