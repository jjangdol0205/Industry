# -*- coding: utf-8 -*-
import re

with open(r'D:\Industry\InvestmentPortal\frontend\src\App.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

old_defs = '''const fB  = (n) => n == null ? '-' : `$${(n/1e9).toFixed(2)}B`;          // 십억 달러
const fM  = (n) => n == null ? '-' : `$${(n/1e6).toFixed(0)}M`;          // 백만 달러
const fP  = (n) => n == null ? '-' : `${(n*100).toFixed(1)}%`;            // 비율(0~1) → %
const fP2 = (n) => n == null ? '-' : `${n.toFixed(1)}%`;                  // 이미 % 값
const fX  = (n) => n == null ? '-' : `${n.toFixed(2)}x`;                  // 배수
const fN  = (n) => n == null ? '-' : n.toFixed(2);                        // 소수
const fK  = (n) => n == null ? '-' : n.toLocaleString();                  // 정수
const fDollar = (n) => n == null ? '-' : `$${n.toFixed(2)}`;              // 달러 단위'''

new_defs = '''const isKrw = (ticker) => ticker && (ticker.endsWith('.KS') || ticker.endsWith('.KQ'));

const fB = (n, t) => {
  if (n == null) return '-';
  if (isKrw(t)) return `₩${(n/1e8).toLocaleString(undefined, {maximumFractionDigits:0})}억`;
  return `$${(n/1e9).toFixed(2)}B`;
};

const fM = (n, t) => {
  if (n == null) return '-';
  if (isKrw(t)) return `₩${(n/1e8).toLocaleString(undefined, {maximumFractionDigits:1})}억`;
  return `$${(n/1e6).toFixed(0)}M`;
};

const fP  = (n) => n == null ? '-' : `${(n*100).toFixed(1)}%`;
const fP2 = (n) => n == null ? '-' : `${n.toFixed(1)}%`;
const fX  = (n) => n == null ? '-' : `${n.toFixed(2)}x`;
const fN  = (n) => n == null ? '-' : n.toFixed(2);
const fK  = (n) => n == null ? '-' : n.toLocaleString();

const fDollar = (n, t) => {
  if (n == null) return '-';
  if (isKrw(t)) return `₩${n.toLocaleString(undefined, {maximumFractionDigits:0})}`;
  return `$${n.toFixed(2)}`;
};'''

if old_defs in text:
    text = text.replace(old_defs, new_defs)
else:
    print('Failed to replace defs. Maybe they are already replaced or formatted differently.')
    # Let's try to find it dynamically if exact match fails
    if 'const isKrw' not in text:
        # fallback
        pass

def replace_calls(text, func_name):
    result = []
    i = 0
    while i < len(text):
        idx = text.find(func_name + '(', i)
        if idx == -1:
            result.append(text[i:])
            break
        result.append(text[i:idx + len(func_name) + 1])
        i = idx + len(func_name) + 1
        
        paren_count = 1
        arg_start = i
        while i < len(text) and paren_count > 0:
            if text[i] == '(':
                paren_count += 1
            elif text[i] == ')':
                paren_count -= 1
            i += 1
        
        arg_str = text[arg_start:i-1]
        
        if 'company?.ticker' not in arg_str:
            result.append(arg_str + ', company?.ticker)')
        else:
            result.append(arg_str + ')')
    return ''.join(result)

text = replace_calls(text, 'fB')
text = replace_calls(text, 'fM')
text = replace_calls(text, 'fDollar')

with open(r'D:\Industry\InvestmentPortal\frontend\src\App.jsx', 'w', encoding='utf-8') as f:
    f.write(text)

print('Successfully replaced all usages.')
