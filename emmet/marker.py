import re
import sublime
from . import expand, validate, get_options

abbr_region_id = 'emmet-abbreviation'

class AbbreviationMarker:
    def __init__(self, view, start, end):
        self.view = view
        self.options = get_options(view, start)
        self.region = None
        self.valid = False
        self.simple = False
        self.matched = False
        self.error = self.error_snippet = None
        self.error_pos = -1
        self.update(start, end)

    def __del__(self):
        regions = self.view.get_regions(abbr_region_id)
        if regions and self.region:
            r1 = regions[0]
            r2 = self.region
            if r1.begin() == r2.begin() and r1.end() == r2.end():
                self.view.erase_regions(abbr_region_id)

        self.view = self.region = self.options = None

    @property
    def abbreviation(self):
        return self.region and self.view.substr(self.region) or None

    def update(self, start, end):
        self.region = sublime.Region(start, end)
        self.mark()
        self.validate()

    def validate(self):
        "Validates currently marked abbreviation"
        regions = self.view.get_regions(abbr_region_id)
        if regions:
            self.region = regions[0]
            data = validate(self.abbreviation, self.options)

            if data['valid']:
                self.valid = True
                self.simple = data['simple']
                self.matched = data['matched']
                self.error = self.error_snippet = None
                self.error_pos = -1
            else:
                self.valid = self.simple = self.matched = False
                self.error = data['error']
                self.error_snippet = data['snippet']
                self.error_pos = data['pos']
            self.mark()
        else:
            self.reset()

        return self.valid

    def mark(self):
        "Marks abbreviation in view with current state"
        self.view.erase_regions(abbr_region_id)
        if self.region:
            scope = '%s.emmet' % (self.valid and 'string' or 'error',)
            self.view.add_regions(abbr_region_id, [self.region], 'string.emmet', '',
                sublime.DRAW_SOLID_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

    def reset(self):
        self.valid = self.simple = self.matched = False
        self.region = self.error = self.error_snippet = None
        self.error_pos = -1
        self.mark()

    def contains(self, pt):
        "Check if current abbreviation range contains given point"
        return self.region and self.region.contains(pt)


    def snippet(self):
        if self.valid:
            return expand(self.abbreviation, self.options)
        return ''

    def preview(self):
        """
        Returns generated preview of current abbreviation: if abbreviation is valid,
        returns expanded snippet, otherwise returns error snippet
        """
        if self.region and self.valid:
            try:
                opt = self.options.copy()
                opt['preview'] = True
                snippet = expand(self.abbreviation, opt)

                lines = [
                    '<div style="padding-left: %dpx"><code>%s</code></div>' % (indent_size(line) * 20, escape_html(line)) for line in snippet.splitlines()
                ]

                return popup_content('\n'.join(lines))

            except Exception as e:
                lines = [
                    '<div><code>%s</code></div>' % escape_html(line) for line in str(e).splitlines()
                ]
                return popup_content('<div class="error">%s</div>' % '\n'.join(lines))

        else:
            return popup_content('<div class="error">%s<br/>%s</div>' % (self.error, self.error_snippet))


def popup_content(content):
    return """
    <body>
        <style>
            body { font-size: 0.85rem; line-height: 1.5rem; }
            pre { display: block }
            .error { color: red }
        </style>
        <div>%s</div>
    </body>
    """ % content


def escape_html(text):
    escaped = { '<': '&lt;', '&': '&amp;', '>': '&gt;' }
    return re.sub(r'[<>&]', lambda m: escaped[m.group(0)], text)


def indent_size(line):
    m = re.match(r'\t+', line)
    if m:
        return len(m.group(0))
    return 0
