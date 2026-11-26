import os
import re
import html
from xml.sax.saxutils import escape

def clean(value):
    value = html.unescape(value)
    return escape(value, {'"': '&quot;'})

def get_attr(tag, attr, nxt=None):
    if nxt:
        match = re.search(r'\b' + attr + r'="(.*?)"\s+' + nxt + r'=', tag, re.DOTALL)
    else:
        match = re.search(r'\b' + attr + r'="(.*?)"\s*/?>', tag, re.DOTALL)
    return match.group(1) if match else ''

def sanitize_leaf(tag):
    text = get_attr(tag, 'text', 'title')
    title = get_attr(tag, 'title', 'description')
    desc = get_attr(tag, 'description', 'xmlUrl')
    url = get_attr(tag, 'xmlUrl', 'type')
    typ = get_attr(tag, 'type')
    return ('<outline text="{t}" title="{ti}" description="{d}" xmlUrl="{u}" type="{ty}" />'
            .format(t=clean(text), ti=clean(title), d=clean(desc), u=clean(url), ty=clean(typ)))

def sanitize_folder(match):
    text, title = match.groups()
    return '<outline text="{t}" title="{ti}">'.format(t=clean(text), ti=clean(title))

def main():
    leaf_re = re.compile(r'<outline\s+text=(?:(?!<outline).)*?xmlUrl=(?:(?!<outline).)*?/>', re.DOTALL)
    folder_re = re.compile(r'<outline\s+text="([^"\n]*)"\s+title="([^"\n]*)"\s*>')

    count = 0
    for dirpath, dirnames, filenames in os.walk('.'):
        if '.git' in dirnames:
            dirnames.remove('.git')
        for filename in filenames:
            if not filename.endswith('.opml'):
                continue
            path = os.path.join(dirpath, filename)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            new = leaf_re.sub(lambda m: sanitize_leaf(m.group(0)), content)
            new = folder_re.sub(sanitize_folder, new)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new)
            count += 1
    print('Sanitized {} OPML files'.format(count))

if __name__ == '__main__':
    main()