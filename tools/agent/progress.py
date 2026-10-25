#!/usr/bin/env python3
"""Обновляет docs/PROGRESS.md: заменяет блок ТЕКУЩАЯ ПОЗИЦИЯ и вставляет запись лога сверху.
usage: progress.py PROGRESS.md position.md entry.md"""
import sys
p, pos, ent = sys.argv[1:4]
s = open(p, encoding='utf-8').read()
pos_t = open(pos, encoding='utf-8').read().strip('\n')
ent_t = open(ent, encoding='utf-8').read().strip('\n')
a = s.index('## ТЕКУЩАЯ ПОЗИЦИЯ')
b = s.index('\n---', a)
s = s[:a] + '## ТЕКУЩАЯ ПОЗИЦИЯ\n' + pos_t + '\n' + s[b:]
marker = '## Лог (новые записи — сверху)\n'
k = s.index(marker) + len(marker)
s = s[:k] + '\n' + ent_t + '\n' + s[k:]
open(p, 'w', encoding='utf-8').write(s)
print('ok')
