import re
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango
from whisp.config import config

_TABLE_RE = re.compile(
    r'^\|[^\n]+\n\|[-:| ]+\|?\n(?:^\|[^\n]*\n?)*',
    re.MULTILINE,
)

class MarkdownHighlighter:
    def __init__(self, buffer, textview=None, editor=None):
        self.buffer = buffer
        self.editor = editor
        self.textview = textview or (editor.textview if editor else None)
        self.search_term = ""
        self.create_tags()
        self.buffer.connect("changed", self.on_changed)
        self.buffer.connect("notify::cursor-position", self.on_cursor_moved)
        # Timeout ID for debouncing
        self.timeout_id = 0
        self.last_cursor_line = -1
        self._image_anchors = []  # list of (TextMark, TextChildAnchor) tuples
        self._table_anchors = []

    def create_tags(self):
        # Headings
        self.tag_h1 = self.buffer.create_tag("h1", weight=Pango.Weight.BOLD, scale=2.0)
        self.tag_h2 = self.buffer.create_tag("h2", weight=Pango.Weight.BOLD, scale=1.5)
        self.tag_h3 = self.buffer.create_tag("h3", weight=Pango.Weight.BOLD, scale=1.25)
        
        # Plain text headings (Orange color, bold, hashes grey)
        self.tag_heading_plain = self.buffer.create_tag("heading_plain", foreground="#d08770", weight=Pango.Weight.BOLD)
        self.tag_hash_plain = self.buffer.create_tag("hash_plain", foreground="#4c566a", weight=Pango.Weight.BOLD)
        
        # Bold, Italic, Underline, and Strikethrough
        self.tag_bold = self.buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        self.tag_italic = self.buffer.create_tag("italic", style=Pango.Style.ITALIC)
        self.tag_underline = self.buffer.create_tag("underline", underline=Pango.Underline.SINGLE)
        self.tag_strikethrough = self.buffer.create_tag("strikethrough", strikethrough=True)
        self.tag_checkbox_checked = self.buffer.create_tag("checkbox_checked", strikethrough=True, foreground="#aaaaaa")
        self.tag_checkbox_icon = self.buffer.create_tag("checkbox_icon", weight=Pango.Weight.BOLD, foreground="#aaaaaa")
        self.tag_list_keyword = self.buffer.create_tag("list_keyword", foreground="#b48ead", weight=Pango.Weight.BOLD, pixels_below_lines=32)
        
        # Link styling
        self.tag_link = self.buffer.create_tag("link", foreground="#81a1c1", underline=Pango.Underline.SINGLE)
        
        # Monospace / Code
        self.tag_code = self.buffer.create_tag("code", family="monospace", background="rgba(128, 128, 128, 0.2)")
        
        # Bullet points
        self.tag_bullet = self.buffer.create_tag("bullet", indent=-15, left_margin=30)
        self.tag_bullet_bold = self.buffer.create_tag("bullet_bold", weight=Pango.Weight.BOLD)
        
        # Comments
        self.tag_comment = self.buffer.create_tag("comment", foreground="#888888", style=Pango.Style.ITALIC)
        
        # Invisible tag for WYSIWYG
        self.tag_invisible = self.buffer.create_tag("invisible", invisible=True)

        # Table styling (raw mode)
        self.tag_table_pipe = self.buffer.create_tag("table_pipe", foreground="#4c566a")
        self.tag_table_sep  = self.buffer.create_tag("table_sep",  foreground="#4c566a", family="monospace")

        self.tag_search = self.buffer.create_tag("search_match", background="#f9f06b", foreground="#000000")

    def set_search_term(self, term):
        self.search_term = term or ""
        self.highlight_search()

    def highlight_search(self):
        start, end = self.buffer.get_bounds()
        self.buffer.remove_tag(self.tag_search, start, end)
        if not self.search_term:
            return
        # Tag only the viewport (+margin); the editor re-runs this on scroll.
        lo, hi = self._search_scan_range()
        base = lo.get_offset()
        text = self.buffer.get_text(lo, hi, True)
        for m in re.finditer(re.escape(self.search_term), text, re.IGNORECASE):
            s_iter = self.buffer.get_iter_at_offset(base + m.start())
            e_iter = self.buffer.get_iter_at_offset(base + m.end())
            self.buffer.apply_tag(self.tag_search, s_iter, e_iter)

    def _search_scan_range(self):
        tv = self.textview
        if tv is None:
            return self.buffer.get_bounds()
        rect = tv.get_visible_rect()
        if rect.height <= 0:
            return self.buffer.get_bounds()
        # Two screenfuls of slack each side so fast scroll stays in the band.
        margin = rect.height * 2
        _, top = tv.get_iter_at_location(0, max(0, rect.y - margin))
        _, bot = tv.get_iter_at_location(0, rect.y + rect.height + margin)
        return top, bot

    def on_cursor_moved(self, buffer, param):
        cursor_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        cursor_line = cursor_iter.get_line()
        if cursor_line != self.last_cursor_line:
            self.last_cursor_line = cursor_line
            if self.timeout_id:
                GLib.source_remove(self.timeout_id)
            self.timeout_id = GLib.idle_add(self.highlight)

    def on_changed(self, buffer):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = GLib.idle_add(self.highlight)

    def _cleanup_anchors(self, anchor_list):
        if not anchor_list:
            return
        self.buffer.handler_block_by_func(self.on_changed)
        try:
            for mark, anchor in reversed(anchor_list):
                if not anchor.get_deleted():
                    it = self.buffer.get_iter_at_mark(mark)
                    end = it.copy()
                    end.forward_char()
                    self.buffer.delete(it, end)
                if not mark.get_deleted():
                    self.buffer.delete_mark(mark)
        finally:
            self.buffer.handler_unblock_by_func(self.on_changed)
        del anchor_list[:]

    def _cleanup_image_anchors(self):
        self._cleanup_anchors(self._image_anchors)

    def _insert_image_anchors(self, image_matches):
        if not image_matches or self.textview is None:
            return
        self.buffer.handler_block_by_func(self.on_changed)
        try:
            for m, full_path in reversed(image_matches):
                it = self.buffer.get_iter_at_offset(m.start(0))
                anchor = self.buffer.create_child_anchor(it)
                mark_it = self.buffer.get_iter_at_offset(m.start(0))
                mark = self.buffer.create_mark(None, mark_it, True)
                self._image_anchors.append((mark, anchor))

                # Apply invisible tag to the text AFTER the anchor (+1 for the anchor char).
                # Done here (not in highlight()) so the range is correct post-insertion.
                text_start = self.buffer.get_iter_at_offset(m.start(0) + 1)
                text_end = self.buffer.get_iter_at_offset(m.end(0) + 1)
                self.buffer.apply_tag(self.tag_invisible, text_start, text_end)

                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        full_path, 400, -1, True
                    )
                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                    picture = Gtk.Picture.new_for_paintable(texture)
                    picture.set_size_request(pixbuf.get_width(), pixbuf.get_height())
                except Exception:
                    picture = Gtk.Picture.new()
                    picture.set_size_request(200, 100)
                picture.set_content_fit(Gtk.ContentFit.CONTAIN)
                picture.set_visible(True)
                self.textview.add_child_at_anchor(picture, anchor)
        finally:
            self.buffer.handler_unblock_by_func(self.on_changed)

    def _make_table_widget(self, table_text):
        SEP_RE = re.compile(r'^\|[-:| ]+\|?\s*$')
        header_cells = None
        data_rows = []
        found_sep = False
        for line in table_text.rstrip('\n').split('\n'):
            line = line.strip()
            if not line.startswith('|'):
                continue
            if SEP_RE.match(line):
                found_sep = True
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            if header_cells is None and not found_sep:
                header_cells = cells
            else:
                data_rows.append(cells)
        if header_cells is None:
            return None
        max_cols = max(len(r) for r in [header_cells] + data_rows) if data_rows else len(header_cells)

        grid = Gtk.Grid()
        grid.set_row_spacing(0)
        grid.set_column_spacing(0)

        for col, cell in enumerate(header_cells):
            label = Gtk.Label()
            label.set_markup(f"<b>{GLib.markup_escape_text(cell)}</b>")
            label.set_xalign(0)
            label.set_margin_start(8)
            label.set_margin_end(8)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            grid.attach(label, col, 0, 1, 1)
        for col in range(len(header_cells), max_cols):
            grid.attach(Gtk.Label(label=""), col, 0, 1, 1)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(sep, 0, 1, max_cols, 1)

        for row_idx, row in enumerate(data_rows):
            for col in range(max_cols):
                cell = row[col] if col < len(row) else ""
                label = Gtk.Label(label=cell)
                label.set_xalign(0)
                label.set_margin_start(8)
                label.set_margin_end(8)
                label.set_margin_top(4)
                label.set_margin_bottom(4)
                grid.attach(label, col, row_idx + 2, 1, 1)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.START)
        frame.set_margin_top(4)
        frame.set_margin_bottom(4)
        frame.set_child(grid)
        frame.set_visible(True)
        return frame

    def _insert_table_anchors(self, table_matches):
        if not table_matches or self.textview is None:
            return
        self.buffer.handler_block_by_func(self.on_changed)
        try:
            for m in reversed(table_matches):
                it = self.buffer.get_iter_at_offset(m.start(0))
                anchor = self.buffer.create_child_anchor(it)
                mark_it = self.buffer.get_iter_at_offset(m.start(0))
                mark = self.buffer.create_mark(None, mark_it, True)
                self._table_anchors.append((mark, anchor))

                text_start = self.buffer.get_iter_at_offset(m.start(0) + 1)
                text_end   = self.buffer.get_iter_at_offset(m.end(0)   + 1)
                self.buffer.apply_tag(self.tag_invisible, text_start, text_end)

                widget = self._make_table_widget(m.group(0))
                if widget:
                    self.textview.add_child_at_anchor(widget, anchor)
        finally:
            self.buffer.handler_unblock_by_func(self.on_changed)

    def highlight(self):
        self.timeout_id = 0
        self._cleanup_image_anchors()
        self._cleanup_anchors(self._table_anchors)
        start, end = self.buffer.get_bounds()
        text = self.buffer.get_text(start, end, True)
        
        cursor_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        cursor_offset = cursor_iter.get_offset()
        
        # Remove all formatting tags first
        self.buffer.remove_all_tags(start, end)
        
        def apply_invisible(m, group_idx=1, outer_match=None):
            check_m = outer_match if outer_match else m
            start_offset = m.start(group_idx)
            end_offset = m.end(group_idx)
            start_iter = self.buffer.get_iter_at_offset(start_offset)
            end_iter = self.buffer.get_iter_at_offset(end_offset)
            
            if not (check_m.start() <= cursor_offset <= check_m.end()):
                self.buffer.apply_tag(self.tag_invisible, start_iter, end_iter)
        
        wysiwyg = False
        if hasattr(self, 'editor') and self.editor and hasattr(self.editor, 'is_wysiwyg_enabled'):
            wysiwyg = self.editor.is_wysiwyg_enabled()
        else:
            wysiwyg = config.get("wysiwyg_mode", False)
        
        # Check if it's a list note
        start_doc = self.buffer.get_start_iter()
        end_doc = start_doc.copy()
        end_doc.forward_to_line_end()
        first_line = self.buffer.get_text(start_doc, end_doc, False).strip().lower()
        is_list_note = bool(re.match(r'^(#{1,6}\s*)?list(\s*[:\s].*)?$', first_line))
        
        if is_list_note:
            self.buffer.apply_tag(self.tag_list_keyword, start_doc, end_doc)
        else:
            # Apply headings (e.g. # Heading)
            for m in re.finditer(r'^(#{1,6}\s+)(.*)$', text, re.MULTILINE):
                level = len(m.group(1).strip())
                start_iter = self.buffer.get_iter_at_offset(m.start())
                hash_end = self.buffer.get_iter_at_offset(m.end(1))
                end_iter = self.buffer.get_iter_at_offset(m.end())
                
                if wysiwyg:
                    tag = getattr(self, f"tag_h{level}", self.tag_h1)
                    self.buffer.apply_tag(tag, start_iter, end_iter)
                    apply_invisible(m, 1, outer_match=m)
                else:
                    self.buffer.apply_tag(self.tag_hash_plain, start_iter, hash_end)
                    self.buffer.apply_tag(self.tag_heading_plain, hash_end, end_iter)
            
        # Apply bullet points (- item or * item) and numbered lists (1. item)
        for m in re.finditer(r'^(\s*(?:[-*+]|\d+\.)\s+)(.*)$', text, re.MULTILINE):
            start_iter = self.buffer.get_iter_at_offset(m.start())
            bullet_end_iter = self.buffer.get_iter_at_offset(m.start() + len(m.group(1)))
            if wysiwyg:
                self.buffer.apply_tag(self.tag_bullet, start_iter, bullet_end_iter)
            self.buffer.apply_tag(self.tag_bullet_bold, start_iter, bullet_end_iter)
            
        # Apply bold (**text**)
        for m in re.finditer(r'(\*\*)(.*?)(\*\*)', text):
            start_iter = self.buffer.get_iter_at_offset(m.start())
            end_iter = self.buffer.get_iter_at_offset(m.end())
            self.buffer.apply_tag(self.tag_bold, start_iter, end_iter)
            if wysiwyg:
                apply_invisible(m, 1)
                apply_invisible(m, 3)
            
        # Apply italic (*text*)
        for m in re.finditer(r'(?<!\*)(\*)([^\*]+)(\*)', text):
            start_iter = self.buffer.get_iter_at_offset(m.start())
            end_iter = self.buffer.get_iter_at_offset(m.end())
            self.buffer.apply_tag(self.tag_italic, start_iter, end_iter)
            if wysiwyg:
                apply_invisible(m, 1)
                apply_invisible(m, 3)
            
        # Apply underline (<u>text</u>)
        for m in re.finditer(r'(<u>)(.*?)(</u>)', text):
            start_iter = self.buffer.get_iter_at_offset(m.start())
            end_iter = self.buffer.get_iter_at_offset(m.end())
            self.buffer.apply_tag(self.tag_underline, start_iter, end_iter)
            if wysiwyg:
                apply_invisible(m, 1, outer_match=m)
                apply_invisible(m, 3, outer_match=m)
            
        # Apply strikethrough (~~text~~)
        for m in re.finditer(r'(~~)(.*?)(~~)', text):
            start_iter = self.buffer.get_iter_at_offset(m.start())
            end_iter = self.buffer.get_iter_at_offset(m.end())
            self.buffer.apply_tag(self.tag_strikethrough, start_iter, end_iter)
            if wysiwyg:
                apply_invisible(m, 1)
                apply_invisible(m, 3)
            
        # Apply checkboxes (☐ or ☑)
        for m in re.finditer(r'^(\s*)([☐☑])\s*(.*)$', text, re.MULTILINE):
            box_start = self.buffer.get_iter_at_offset(m.start(2))
            box_end = self.buffer.get_iter_at_offset(m.end(2))
            line_end = self.buffer.get_iter_at_offset(m.end(3))
            
            self.buffer.apply_tag(self.tag_checkbox_icon, box_start, box_end)
            
            if m.group(2) == '☑':
                self.buffer.apply_tag(self.tag_checkbox_checked, box_start, line_end)

        # Apply link formatting for Markdown links [text](url) — exclude image syntax ![alt](url)
        for m in re.finditer(r'(?<!!)\[(.*?)\]\((.*?)\)', text):
            text_start = self.buffer.get_iter_at_offset(m.start(1))
            text_end = self.buffer.get_iter_at_offset(m.end(1))
            self.buffer.apply_tag(self.tag_link, text_start, text_end)
            
            if wysiwyg:
                # If cursor is not on the link, hide everything except the text
                if not (m.start(0) <= cursor_offset <= m.end(0)):
                    # Hide '['
                    start_iter = self.buffer.get_iter_at_offset(m.start(0))
                    end_iter = self.buffer.get_iter_at_offset(m.start(1))
                    self.buffer.apply_tag(self.tag_invisible, start_iter, end_iter)
                    
                    # Hide '](url)'
                    start_iter = self.buffer.get_iter_at_offset(m.end(1))
                    end_iter = self.buffer.get_iter_at_offset(m.end(0))
                    self.buffer.apply_tag(self.tag_invisible, start_iter, end_iter)

        # Apply link formatting for bare URLs
        for m in re.finditer(r'(?<!\()https?://[^\s]+', text):
            start_iter = self.buffer.get_iter_at_offset(m.start())
            end_iter = self.buffer.get_iter_at_offset(m.end())
            self.buffer.apply_tag(self.tag_link, start_iter, end_iter)

        # Apply code (`text`)
        for m in re.finditer(r'(`)(.*?)(`)', text):
            if wysiwyg and not (m.start() <= cursor_offset <= m.end()):
                # Hide opening backtick
                start_iter = self.buffer.get_iter_at_offset(m.start(1))
                end_iter = self.buffer.get_iter_at_offset(m.end(1))
                self.buffer.apply_tag(self.tag_invisible, start_iter, end_iter)
                
                # Hide closing backtick
                start_iter = self.buffer.get_iter_at_offset(m.start(3))
                end_iter = self.buffer.get_iter_at_offset(m.end(3))
                self.buffer.apply_tag(self.tag_invisible, start_iter, end_iter)

                # Apply code styling to inner text only
                start_iter = self.buffer.get_iter_at_offset(m.start(2))
                end_iter = self.buffer.get_iter_at_offset(m.end(2))
                self.buffer.apply_tag(self.tag_code, start_iter, end_iter)
            else:
                # Apply code styling to the whole match including backticks
                start_iter = self.buffer.get_iter_at_offset(m.start())
                end_iter = self.buffer.get_iter_at_offset(m.end())
                self.buffer.apply_tag(self.tag_code, start_iter, end_iter)
            
        # Apply comments (// text)
        for m in re.finditer(r'^(\s*(?:[☐☑]\s*)?//)(.*)$', text, re.MULTILINE):
            start_iter = self.buffer.get_iter_at_offset(m.start())
            end_iter = self.buffer.get_iter_at_offset(m.end())
            self.buffer.apply_tag(self.tag_comment, start_iter, end_iter)

        # Apply table formatting — inline widget in WYSIWYG, styled pipes in raw mode
        table_matches_to_anchor = []
        for m in _TABLE_RE.finditer(text):
            table_start_line = self.buffer.get_iter_at_offset(m.start(0)).get_line()
            # end(0) may point at start of next line; step back 1 char to get last table line
            end_check_offset = max(m.start(0), m.end(0) - 1)
            table_end_line = self.buffer.get_iter_at_offset(end_check_offset).get_line()
            cursor_on_table = table_start_line <= cursor_iter.get_line() <= table_end_line

            if wysiwyg and not cursor_on_table:
                table_matches_to_anchor.append(m)
            else:
                # Style pipe chars muted and separator row distinctly
                table_text = m.group(0)
                for pipe_m in re.finditer(r'\|', table_text):
                    pi = self.buffer.get_iter_at_offset(m.start(0) + pipe_m.start())
                    pe = self.buffer.get_iter_at_offset(m.start(0) + pipe_m.end())
                    self.buffer.apply_tag(self.tag_table_pipe, pi, pe)
                sep_m = re.search(r'^(\|[-:| ]+\|?\n?)$', table_text, re.MULTILINE)
                if sep_m:
                    si = self.buffer.get_iter_at_offset(m.start(0) + sep_m.start())
                    se = self.buffer.get_iter_at_offset(m.start(0) + sep_m.end())
                    self.buffer.apply_tag(self.tag_table_sep, si, se)

        # Apply image formatting for ![alt](path) — hide syntax in WYSIWYG, show inline widget
        image_matches_to_anchor = []
        for m in re.finditer(r'!\[([^\]]*)\]\(([^)]+\.(?:png|jpg|jpeg|gif|webp))\)', text):
            if wysiwyg and not (m.start(0) <= cursor_offset <= m.end(0)):
                if self.editor and hasattr(self.editor, 'file_path'):
                    full_path = str(self.editor.file_path.parent / m.group(2))
                    image_matches_to_anchor.append((m, full_path))

        # highlight_search runs before anchor insertion so its offset calculations stay clean
        self.highlight_search()

        if image_matches_to_anchor:
            self._insert_image_anchors(image_matches_to_anchor)
        if table_matches_to_anchor:
            self._insert_table_anchors(table_matches_to_anchor)

        return False
