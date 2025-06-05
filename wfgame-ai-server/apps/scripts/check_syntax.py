import ast
import sys

try:
    with open('utils.py', 'r', encoding='utf-8') as f:
        content = f.read()
    ast.parse(content)
    print('Syntax OK')
except SyntaxError as e:
    print(f'Syntax Error at line {e.lineno}: {e.msg}')
    if e.text:
        print(f'Text: {e.text.strip()}')
except Exception as e:
    print(f'Error: {e}')
