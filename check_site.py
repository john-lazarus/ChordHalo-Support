"""Check the static website before publishing: python3 check_site.py."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
PAGES = ('index.html', 'support.html', 'privacy.html', 'terms.html', 'data-deletion.html')


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags, self.links, self.ids = [], [], set()
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, 'Duplicate element ID'
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.links.append(attrs[key])


def check(root=ROOT):
    parsed = {name: Page((root / name).read_text()) for name in PAGES}
    for name, page in parsed.items():
        tags = [tag for tag, _ in page.tags]
        assert tags.count('h1') == 1, (name, 'One main heading required')
        assert tags.count('title') == 1, (name, 'Missing title')
        assert 'script' not in tags and 'iframe' not in tags, (name, 'Unexpected embedded content')
        assert any(tag == 'meta' and attrs.get('name') == 'viewport' for tag, attrs in page.tags)
        assert any(tag == 'link' and attrs.get('rel') == 'canonical' for tag, attrs in page.tags)
        assert set(PAGES).issubset({urlsplit(link).path for link in page.links}), (name, 'Missing navigation')
        for link in page.links:
            parts = urlsplit(link)
            if parts.scheme:
                assert parts.scheme in ('https', 'mailto'), (name, link)
                if parts.scheme == 'mailto':
                    assert parts.path == 'ronnie.lazarus.dev@gmail.com', (name, 'Unexpected contact address')
                continue
            assert not parts.netloc, (name, 'Protocol-relative URL')
            path = (root / unquote(parts.path or name)).resolve()
            assert path.is_relative_to(root.resolve()) and path.is_file(), (name, link)
            if parts.fragment:
                assert path.name in parsed and parts.fragment in parsed[path.name].ids, (name, link)
        for tag, attrs in page.tags:
            if tag == 'img':
                assert 'alt' in attrs and 'width' in attrs and 'height' in attrs, (name, 'Incomplete image')
    assert (root / 'assets/app-icon.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert (root / '.nojekyll').is_file()
    print(f'PASS: {len(parsed)} pages; local links, fragments, navigation, contact, metadata and image checked.')


if __name__ == '__main__':
    check()
