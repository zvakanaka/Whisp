import re
import os
import shutil
from pathlib import Path
from gi.repository import Gtk, Adw, Gdk, Gio, GLib, Pango
from whisp.config import config, DATA_DIR, TRASH_DIR
from whisp.editor import NoteEditor
from whisp.text_search import iter_body_match_offsets

class ThemeSnippet(Gtk.ToggleButton):
    def __init__(self, theme_id, group=None):
        super().__init__(group=group)
        self.theme_id = theme_id
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.add_css_class("theme-snippet-btn")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("theme-snippet-preview")
        box.add_css_class(f"paper-{theme_id}")
        
        # Add fake text lines to simulate an editor
        for width in [60, 80, 40]:
            line = Gtk.Box()
            line.add_css_class("fake-text-line")
            line.set_size_request(width, 4)
            line.set_halign(Gtk.Align.START)
            box.append(line)
            
        self.set_child(box)

shortcuts_xml = """
<interface>
  <object class="AdwShortcutsDialog" id="shortcuts_dialog">
    <child>
      <object class="AdwShortcutsSection">
        <property name="title">General</property>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Create New Note</property>
            <property name="accelerator">&lt;Primary&gt;n</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Delete Note</property>
            <property name="accelerator">&lt;Primary&gt;Delete</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Undo Delete</property>
            <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;t</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Previous Note</property>
            <property name="accelerator">&lt;Primary&gt;bracketleft</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Next Note</property>
            <property name="accelerator">&lt;Primary&gt;bracketright</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">First Note</property>
            <property name="accelerator">&lt;Alt&gt;f</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Last Note</property>
            <property name="accelerator">&lt;Alt&gt;l</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Pin Note</property>
            <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;p</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Move Note to Front</property>
            <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;m</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Preferences</property>
            <property name="accelerator">&lt;Primary&gt;comma</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Quit</property>
            <property name="accelerator">&lt;Primary&gt;q</property>
          </object>
        </child>
      </object>
    </child>
    
    <child>
      <object class="AdwShortcutsSection">
        <property name="title">Editor</property>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Search Notes</property>
            <property name="accelerator">&lt;Primary&gt;f</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Toggle Checkbox</property>
            <property name="accelerator">&lt;Primary&gt;s</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Paste Plain Text</property>
            <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;v</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Copy Entire Note</property>
            <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;c</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Shorten Selected URL</property>
            <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;l</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Bold Text</property>
            <property name="accelerator">&lt;Primary&gt;b</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Italic Text</property>
            <property name="accelerator">&lt;Primary&gt;i</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Underline Text</property>
            <property name="accelerator">&lt;Primary&gt;u</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Strikethrough Text</property>
            <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;s</property>
          </object>
        </child>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Insert Emoji</property>
            <property name="accelerator">&lt;Primary&gt;period</property>
          </object>
        </child>
      </object>
    </child>

    <child>
      <object class="AdwShortcutsSection">
        <property name="title">Modes</property>
        <child>
          <object class="AdwShortcutsItem">
            <property name="title">Toggle WYSIWYG Mode</property>
            <property name="accelerator">&lt;Primary&gt;e</property>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>
"""

class ChangelogWindow(Adw.Dialog):
    def __init__(self, version, releases_list, parent=None):
        super().__init__(title="What's New")
        self.set_content_width(550)
        self.set_content_height(600)
        
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        toolbar_view.add_top_bar(header)
        
        # Add close button explicitly to Adw.Dialog header if we want, or just rely on dialog close
        close_btn = Gtk.Button(icon_name="window-close-symbolic")
        close_btn.add_css_class("flat")
        close_btn.connect("clicked", lambda _: self.close())
        header.pack_end(close_btn)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_propagate_natural_height(True)
        toolbar_view.set_content(scrolled)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        scrolled.set_child(content_box)
        
        if not isinstance(releases_list, list):
            # Fallback if text was passed somehow
            releases_list = [{"version": version, "date": "", "description": releases_list}]
            
        for release in releases_list:
            v_str = release.get("version", "Unknown")
            date_str = release.get("date", "")
            desc_text = release.get("description", "")
            
            listbox = Gtk.ListBox()
            listbox.add_css_class("boxed-list")
            listbox.set_selection_mode(Gtk.SelectionMode.NONE)
            
            card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            card_box.set_margin_start(20)
            card_box.set_margin_end(20)
            card_box.set_margin_top(20)
            card_box.set_margin_bottom(20)
            
            header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            
            title_lbl = Gtk.Label(label=f"<b>Whisp {v_str}</b>")
            title_lbl.set_use_markup(True)
            title_lbl.add_css_class("title-2")
            title_lbl.set_halign(Gtk.Align.START)
            title_lbl.set_hexpand(True)
            
            date_lbl = Gtk.Label(label=f"<small>{date_str}</small>")
            date_lbl.set_use_markup(True)
            date_lbl.add_css_class("dim-label")
            date_lbl.set_halign(Gtk.Align.END)
            
            header_box.append(title_lbl)
            if date_str:
                header_box.append(date_lbl)
            
            desc_lbl = Gtk.Label(wrap=True, xalign=0)
            desc_lbl.set_markup(desc_text)
            desc_lbl.set_margin_top(16)
            
            card_box.append(header_box)
            card_box.append(desc_lbl)
            
            row = Gtk.ListBoxRow()
            row.set_child(card_box)
            listbox.append(row)
            
            content_box.append(listbox)
            
        # Pin the buttons to the bottom of the ToolbarView
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(12)
        btn_box.set_margin_bottom(12)
        
        donate_btn = Gtk.Button(label="Donate")
        donate_btn.add_css_class("pill")
        donate_btn.set_size_request(120, -1)
        donate_btn.connect("clicked", lambda _: Gio.AppInfo.launch_default_for_uri("https://tanaybhomia.github.io/Whisp/donate.html", None))
        btn_box.append(donate_btn)

        btn = Gtk.Button(label="Awesome! Continue")
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_size_request(160, -1)
        btn.connect("clicked", lambda _: self.close())
        btn_box.append(btn)
        
        toolbar_view.add_bottom_bar(btn_box)
        
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_ctrl)


    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

class WhispWindow(Adw.ApplicationWindow):
    PAGE_SIZE = 20  # result rows rendered per page; more load as the user scrolls

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Window State
        width = config.get("window_width")
        height = config.get("window_height")
        if width is None or height is None:
            width = 450
            height = 700
        self.set_default_size(int(width), int(height))
        if config.get("is_maximized"):
            self.maximize()
            
        from whisp.main import IS_DEV_MODE
        title = "Whisp (Development)" if IS_DEV_MODE else "Whisp"
        self.set_title(title)
        self.connect("close-request", self.on_close_request)
        
        app = self.get_application()
        if config.get("run_in_background", False):
            app.hold()
        
        # Font and Theme styling
        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.apply_theme()
        
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        import json
        self.metadata = {}
        meta_file = DATA_DIR / "metadata.json"
        if meta_file.exists():
            try:
                self.metadata = json.loads(meta_file.read_text())
            except:
                pass
        self._ignore_pin_toggle = False

        self.toolbar_view = Adw.ToolbarView()
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(self.toolbar_view)
        self.set_content(self.toast_overlay)
        
        self.last_deleted_file = None

        # Actions
        new_note_action = Gio.SimpleAction.new("new-note", None)
        new_note_action.connect("activate", self.on_new_note)
        self.add_action(new_note_action)
        
        undo_action = Gio.SimpleAction.new("undo-delete", None)
        undo_action.connect("activate", self.on_undo_delete)
        self.add_action(undo_action)
        
        shortcuts_action = Gio.SimpleAction.new("show-shortcuts", None)
        shortcuts_action.connect("activate", self.on_show_shortcuts)
        self.add_action(shortcuts_action)
        
        del_note_action = Gio.SimpleAction.new("delete-note", None)
        del_note_action.connect("activate", self.on_delete_note)
        self.add_action(del_note_action)
        
        pref_action = Gio.SimpleAction.new("preferences", None)
        pref_action.connect("activate", self.on_preferences)
        self.add_action(pref_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.close())
        self.add_action(quit_action)
        
        nav_next_action = Gio.SimpleAction.new("nav-next", None)
        nav_next_action.connect("activate", self.on_nav_next)
        self.add_action(nav_next_action)
        
        nav_prev_action = Gio.SimpleAction.new("nav-prev", None)
        nav_prev_action.connect("activate", self.on_nav_prev)
        self.add_action(nav_prev_action)
        
        wysiwyg_action = Gio.SimpleAction.new("toggle-wysiwyg", None)
        wysiwyg_action.connect("activate", self.on_wysiwyg_shortcut)
        self.add_action(wysiwyg_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)
        
        whats_new_action = Gio.SimpleAction.new("whats-new", None)
        whats_new_action.connect("activate", self.on_whats_new)
        self.add_action(whats_new_action)

        search_action = Gio.SimpleAction.new("search", None)
        search_action.connect("activate", self.on_search_shortcut)
        self.add_action(search_action)

        pin_note_action = Gio.SimpleAction.new("pin-note", None)
        pin_note_action.connect("activate", self.on_pin_note)
        self.add_action(pin_note_action)

        nav_first_action = Gio.SimpleAction.new("nav-first", None)
        nav_first_action.connect("activate", self.on_nav_first)
        self.add_action(nav_first_action)

        nav_last_action = Gio.SimpleAction.new("nav-last", None)
        nav_last_action.connect("activate", self.on_nav_last)
        self.add_action(nav_last_action)

        copy_note_action = Gio.SimpleAction.new("copy-note", None)
        copy_note_action.connect("activate", self.on_copy_note)
        self.add_action(copy_note_action)

        bump_note_action = Gio.SimpleAction.new("bump-note", None)
        bump_note_action.connect("activate", self.on_bump_note)
        self.add_action(bump_note_action)

        # HeaderBar
        self.header_bar = Adw.HeaderBar()
        self.header_bar.add_css_class("flat")
        self.toolbar_view.add_top_bar(self.header_bar)
        
        # WYSIWYG Toggle Button
        self.wysiwyg_btn = Gtk.ToggleButton(icon_name="view-reveal-symbolic")
        self.wysiwyg_btn.set_tooltip_text("Toggle Live Formatting")
        self.wysiwyg_btn.set_active(config.get("wysiwyg_mode", False))
        self.wysiwyg_btn.connect("toggled", self.on_wysiwyg_toggled)
        self.header_bar.pack_start(self.wysiwyg_btn)

        # Delete Note Button
        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.set_action_name("win.delete-note")
        del_btn.add_css_class("destructive-action")
        self.header_bar.pack_start(del_btn)

        # Pin Note Button
        self.pin_btn = Gtk.ToggleButton(icon_name="io.github.tanaybhomia.Whisp-pin-symbolic")
        self.pin_btn.set_tooltip_text("Pin Note")
        self.pin_btn.connect("toggled", self.on_pin_note_toggled)
        self.header_bar.pack_start(self.pin_btn)

        # Search Toggle Button
        self.search_btn = Gtk.MenuButton()
        self.search_btn.set_icon_name("system-search-symbolic")
        self.header_bar.pack_end(self.search_btn)

        self.popover = Gtk.Popover()
        # Non-modal so the note stays scrollable while searching; closed via Escape.
        self.popover.set_autohide(False)
        self.search_btn.set_popover(self.popover)
        self.popover.connect("notify::visible", self.on_popover_visible)

        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        popover_box.set_margin_top(12)
        popover_box.set_margin_bottom(12)
        popover_box.set_margin_start(12)
        popover_box.set_margin_end(12)
        popover_box.set_size_request(320, -1)
        self.popover.set_child(popover_box)

        self.search_entry = Gtk.SearchEntry()
        self.search_timeout_id = 0
        self._row_iter = None
        self._note_cache = {}
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("stop-search", lambda e: self.popover.popdown())
        popover_box.append(self.search_entry)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_min_content_width(296)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.search_scrolled = scrolled
        # Infinite scroll: load more on reaching the bottom; prefetch before it.
        scrolled.connect("edge-reached", self.on_search_edge_reached)
        scrolled.get_vadjustment().connect("value-changed", self.on_search_scrolled)
        popover_box.append(scrolled)

        self.note_listbox = Gtk.ListBox()
        self.note_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.note_listbox.add_css_class("boxed-list")
        self.note_listbox.connect("row-activated", self.on_note_row_activated)
        scrolled.set_child(self.note_listbox)


        # Hamburger menu
        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("open-menu-symbolic")
        
        theme_item = Gio.MenuItem.new(None, None)
        theme_item.set_attribute_value("custom", GLib.Variant.new_string("theme-switcher"))
        
        main_menu = Gio.Menu()
        main_menu.append_item(theme_item)
        
        section = Gio.Menu()
        section.append("What's New", "win.whats-new")
        section.append("Keyboard Shortcuts", "win.show-shortcuts")
        section.append("Preferences", "win.preferences")
        section.append("About Whisp", "win.about")
        main_menu.append_section(None, section)
        
        popover = Gtk.PopoverMenu.new_from_model(main_menu)
        
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        theme_box.set_halign(Gtk.Align.CENTER)
        theme_box.set_margin_top(8)
        theme_box.set_margin_bottom(8)
        theme_box.set_margin_start(12)
        theme_box.set_margin_end(12)
        
        self.btn_system = Gtk.ToggleButton()
        self.btn_system.add_css_class("theme-btn")
        self.btn_system.add_css_class("system")
        self.btn_system.connect("toggled", self.on_theme_btn_toggled, "system")
        
        self.btn_light = Gtk.ToggleButton()
        self.btn_light.add_css_class("theme-btn")
        self.btn_light.add_css_class("light")
        self.btn_light.set_group(self.btn_system)
        self.btn_light.connect("toggled", self.on_theme_btn_toggled, "light")
        
        self.btn_dark = Gtk.ToggleButton()
        self.btn_dark.add_css_class("theme-btn")
        self.btn_dark.add_css_class("dark")
        self.btn_dark.set_group(self.btn_system)
        self.btn_dark.connect("toggled", self.on_theme_btn_toggled, "dark")
        
        theme_box.append(self.btn_system)
        theme_box.append(self.btn_light)
        theme_box.append(self.btn_dark)
        
        popover.add_child(theme_box, "theme-switcher")
        self.menu_button.set_popover(popover)
        self.header_bar.pack_end(self.menu_button)

        # Apply initial theme state
        current_theme = config.get("color_scheme", "system")
        if current_theme == "light":
            self.btn_light.set_active(True)
        elif current_theme == "dark":
            self.btn_dark.set_active(True)
        else:
            self.btn_system.set_active(True)
            
        self._apply_color_scheme(current_theme)

        # Carousel
        self.carousel = Adw.Carousel()
        self.carousel.set_opacity(0)
        self.carousel.set_spacing(16)
        self.carousel.set_interactive(True)
        self.carousel.connect("page-changed", self.on_page_changed)
        self.carousel.connect("notify::position", self.on_carousel_position_notify)
        self.toolbar_view.set_content(self.carousel)

        # Wheel paging is reimplemented in on_carousel_scroll; touchpad is untouched.
        self.carousel.set_allow_scroll_wheel(False)
        self._scroll_last_time = 0.0
        self._scroll_changes_note = False
        scroll_ctrl = Gtk.EventControllerScroll()
        scroll_ctrl.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        scroll_ctrl.connect("scroll", self.on_carousel_scroll)
        self.carousel.add_controller(scroll_ctrl)

    def on_theme_btn_toggled(self, btn, scheme):
        if btn.get_active():
            config.set("color_scheme", scheme)
            self._apply_color_scheme(scheme)

    def _apply_color_scheme(self, scheme):
        manager = Adw.StyleManager.get_default()
        if scheme == "light":
            manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif scheme == "dark":
            manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def _get_latest_release_info(self, last_seen="0.0.0", only_latest=False, as_list=False):
        import xml.etree.ElementTree as ET
        from pathlib import Path
        try:
            meta_path = Path("/app/share/metainfo/io.github.tanaybhomia.Whisp.metainfo.xml")
            if not meta_path.exists():
                meta_path = Path(__file__).parent.parent.parent / "data" / "io.github.tanaybhomia.Whisp.metainfo.xml"
                
            tree = ET.parse(meta_path)
            root = tree.getroot()
            releases = root.find("releases")
            
            def parse_ver(v_str):
                try:
                    return tuple(map(int, v_str.split('.')))
                except Exception:
                    return (0, 0, 0)
                    
            last_seen_tuple = parse_ver(last_seen)
            
            if releases is not None:
                description_text = ""
                latest_version = "Unknown"
                releases_list = []
                
                for i, release in enumerate(releases.findall("release")):
                    version = release.attrib.get("version", "Unknown")
                    date = release.attrib.get("date", "")
                    if i == 0:
                        latest_version = version
                        
                    ver_tuple = parse_ver(version)
                    if ver_tuple <= last_seen_tuple or (only_latest and i > 0):
                        break
                        
                    release_desc = ""
                    if not as_list:
                        description_text += f"<span size='large' weight='bold'>v{version}</span>\n"
                    
                    desc_node = release.find("description")
                    if desc_node is not None:
                        for child in desc_node:
                            if child.tag == "p":
                                text = "".join(child.itertext()).strip()
                                if text:
                                    escaped = GLib.markup_escape_text(text)
                                    if child.find("em") is not None:
                                        release_desc += f"<b>{escaped}</b>\n\n"
                                    else:
                                        release_desc += f"{escaped}\n\n"
                            elif child.tag == "ul":
                                for li in child.findall("li"):
                                    if li.text:
                                        release_desc += f"• {GLib.markup_escape_text(li.text.strip())}\n\n"
                                release_desc += "\n"
                                
                    releases_list.append({"version": version, "date": date, "description": release_desc.strip()})
                    description_text += release_desc
                    
                if as_list:
                    return latest_version, releases_list
                return latest_version, description_text.strip()
        except Exception:
            pass
        if as_list:
            return "Unknown", []
        return "Unknown", ""

    def _get_dynamic_version(self):
        version, _ = self._get_latest_release_info(only_latest=True)
        return version
        
    def on_whats_new(self, action, param):
        latest_version, releases_list = self._get_latest_release_info(last_seen="0.0.0", only_latest=False, as_list=True)
        if releases_list:
            ChangelogWindow(latest_version, releases_list, parent=self).present(self)

    def on_about(self, action, param):
        version = self._get_dynamic_version()
        about = Adw.AboutDialog(
            application_name="Whisp",
            application_icon="io.github.tanaybhomia.Whisp",
            developer_name="Tanay Bhomia",
            developers=["Tanay Bhomia"],
            version=version,
            website="https://github.com/tanaybhomia/Whisp",
            issue_url="https://github.com/tanaybhomia/Whisp/issues",
            support_url="https://tanaybhomia.github.io/Whisp/donate.html",
            license_type=Gtk.License.GPL_3_0
        )
        about.present(self)

    def on_nav_next(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            return
        current = int(round(self.carousel.get_position()))
        if current < n_pages - 1:
            editor = self.carousel.get_nth_page(current + 1)
            self.carousel.scroll_to(editor, True)
            GLib.idle_add(lambda: [editor.textview.grab_focus(), False][-1])
            
    def on_nav_prev(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            return
        current = int(round(self.carousel.get_position()))
        if current > 0:
            editor = self.carousel.get_nth_page(current - 1)
            self.carousel.scroll_to(editor, True)
            GLib.idle_add(lambda: [editor.textview.grab_focus(), False][-1])

    def on_carousel_scroll(self, controller, dx, dy):
        if controller.get_unit() != Gdk.ScrollUnit.WHEEL or dy == 0:
            return False
        editor = self.get_current_editor()
        if editor is None:
            return False

        import time
        now = time.monotonic()
        # A gap between ticks marks a new scroll motion.
        new_motion = now - self._scroll_last_time > 0.15
        self._scroll_last_time = now

        vadj = editor.scrolled.get_vadjustment()
        direction = 1 if dy > 0 else -1
        at_top = vadj.get_value() <= vadj.get_lower() + 1
        at_bottom = vadj.get_value() + vadj.get_page_size() >= vadj.get_upper() - 1
        at_edge = (direction > 0 and at_bottom) or (direction < 0 and at_top)

        # A motion changes note only if it starts at the edge.
        if new_motion:
            self._scroll_changes_note = at_edge
            if at_edge:
                self._wheel_change_note(direction)
        return self._scroll_changes_note

    def _wheel_change_note(self, direction):
        n_pages = self.carousel.get_n_pages()
        target = int(round(self.carousel.get_position())) + direction
        if target < 0 or target >= n_pages:
            return
        editor = self.carousel.get_nth_page(target)
        self.carousel.scroll_to(editor, True)

        # Land on the edge we enter from, so reversing the scroll goes back.
        def place():
            vadj = editor.scrolled.get_vadjustment()
            vadj.set_value(vadj.get_lower() if direction > 0
                           else vadj.get_upper() - vadj.get_page_size())
            editor.textview.grab_focus()
            return False
        GLib.idle_add(place)
        GLib.timeout_add(50, place)

    def on_wysiwyg_toggled(self, btn):
        if hasattr(self, '_ignore_wysiwyg_toggle') and self._ignore_wysiwyg_toggle:
            return
            
        scope = config.get("wysiwyg_scope", "global")
        active = btn.get_active()
        
        if scope == "global":
            config.set("wysiwyg_mode", active)
            for i in range(self.carousel.get_n_pages()):
                editor = self.carousel.get_nth_page(i)
                editor.highlighter.highlight()
        else:
            editor = self.get_current_editor()
            if editor:
                fname = editor.file_path.name
                if fname not in self.metadata:
                    self.metadata[fname] = {}
                self.metadata[fname]["wysiwyg"] = active
                self.save_metadata()
                editor.highlighter.highlight()
            
    def on_wysiwyg_shortcut(self, action, param):
        self.wysiwyg_btn.set_active(not self.wysiwyg_btn.get_active())

    def on_show_shortcuts(self, action, param):
        builder = Gtk.Builder.new_from_string(shortcuts_xml, -1)
        dialog = builder.get_object("shortcuts_dialog")
        dialog.present(self)

    def save_metadata(self):
        import json
        meta_file = DATA_DIR / "metadata.json"
        meta_file.write_text(json.dumps(self.metadata))

    def on_pin_note_toggled(self, btn):
        if self._ignore_pin_toggle:
            return
            
        try:
            current_page_idx = int(round(self.carousel.get_position()))
            if current_page_idx < 0 or current_page_idx >= self.carousel.get_n_pages():
                return
                
            current_page = self.carousel.get_nth_page(current_page_idx)
            if not current_page:
                return
                
            is_pinned = btn.get_active()
            fname = current_page.file_path.name
            
            if fname not in self.metadata:
                self.metadata[fname] = {}
            self.metadata[fname]["pinned"] = is_pinned
            self.save_metadata()
            
            if is_pinned:
                self.carousel.remove(current_page)
                self.carousel.insert(current_page, 0)
                
                def animate_pin():
                    self.carousel.scroll_to(current_page, True)
                    current_page.textview.grab_focus()
                    return False
                
                GLib.idle_add(animate_pin)
                GLib.timeout_add(50, animate_pin)
                
                self.toast_overlay.add_toast(Adw.Toast.new("Note Pinned to front"))
            else:
                self.carousel.remove(current_page)
                target_pos = 0
                current_mtime = os.path.getmtime(current_page.file_path) if current_page.file_path.exists() else 0
                n_pages = self.carousel.get_n_pages()
                for i in range(n_pages - 1): # Ignore empty note at end
                    p = self.carousel.get_nth_page(i)
                    p_pinned = self.metadata.get(p.file_path.name, {}).get("pinned", False)
                    if p_pinned:
                        target_pos = i + 1
                        continue
                    p_mtime = os.path.getmtime(p.file_path) if p.file_path.exists() else 0
                    if current_mtime < p_mtime:
                        break
                    target_pos = i + 1
                    
                self.carousel.insert(current_page, target_pos)
                
                def animate_unpin():
                    self.carousel.scroll_to(current_page, True)
                    current_page.textview.grab_focus()
                    return False
                
                GLib.idle_add(animate_unpin)
                GLib.timeout_add(50, animate_unpin)
                
                self.toast_overlay.add_toast(Adw.Toast.new("Note Unpinned"))
                
        except Exception as e:
            print("Error toggling pin:", e)

    def on_pin_note(self, action=None, param=None):
        self.pin_btn.set_active(not self.pin_btn.get_active())

    def load_notes(self, skip_restore=False):
        is_first_run = config.get("first_run", True)
        if is_first_run:
            config.set("first_run", False)
            welcome_file = DATA_DIR / "Welcome to Whisp.md"
            if not welcome_file.exists():
                welcome_text = (
                    "# 👋 Welcome to Whisp!\n\n"
                    "Whisp is the frictionless anti-note. There are no save buttons or files to manage here.\n\n"
                    "## Navigation\n"
                    "👉 **Swipe left and right** on your touchpad (or use `Ctrl+[` and `Ctrl+]`) to switch between notes.\n"
                    "➕ To create a new note, simply swipe past the last note!\n\n"
                    "## Features\n"
                    "☑ **Checklists**: Press `Ctrl+S` on any line to instantly create or toggle a checkbox.\n"
                    "🔗 **Smart Links**: Paste any long URL, and Whisp will automatically shorten it to keep your notes clean.\n"
                    "📋 **Plain Paste**: Use `Ctrl+Shift+V` to paste text cleanly without weird formatting.\n"
                    "🎨 **Themes**: Open Preferences (`Ctrl+,`) to pick a paper background (like Grid or Dotted) and color scheme.\n\n"
                    "📖 **Manual**: For a full list of features, check out the [User Manual](https://tanaybhomia.github.io/Whisp/manual.html)\n\n"
                    "🗑️ Press `Ctrl+D` to delete this note when you're done reading it!"
                )
                welcome_file.write_text(welcome_text, encoding='utf-8')
                
        files = sorted(DATA_DIR.glob("*.md"), key=lambda f: os.path.getmtime(f) if f.exists() else 0, reverse=True)
        
        archive_days = config.get("archive_days", 0)
        import time
        now = time.time()
        
        active_files = []
        pinned_files = []
        for f in files:
            if not f.exists():
                continue
                
            # Clean up completely empty files on disk during startup
            try:
                if not f.read_text(encoding='utf-8').strip():
                    f.unlink(missing_ok=True)
                    continue
            except Exception:
                pass
                
            is_pinned = self.metadata.get(f.name, {}).get("pinned", False)
            if is_pinned:
                pinned_files.append(f)
                continue
                
            if archive_days > 0:
                age_days = (now - os.path.getmtime(f)) / (24 * 3600)
                if age_days > archive_days:
                    continue
            active_files.append(f)
            
        max_notes = config.get("max_carousel_size", 10)
        if max_notes > 0:
            recent_files = active_files[:max_notes]
        else:
            recent_files = active_files
        
        if not recent_files and not pinned_files:
            self.add_note(grab_focus=False)
        else:
            for f in reversed(pinned_files):
                self.add_note(f, grab_focus=False)
            for f in reversed(recent_files):
                self.add_note(f, grab_focus=False)
        
        self.ensure_empty_note_at_end()
        
        n_pages = self.carousel.get_n_pages()
        if n_pages > 0:
            target_idx = n_pages - 2 if n_pages > 1 else 0
            
            startup_behavior = config.get("startup_behavior", "last_note")
            if startup_behavior == "empty_note":
                target_idx = n_pages - 1
            else:
                last_active = config.get("last_active_note")
                if last_active:
                    for i in range(n_pages):
                        if str(self.carousel.get_nth_page(i).file_path) == last_active:
                            target_idx = i
                            break
                        
            target_editor = self.carousel.get_nth_page(target_idx)
            
            def restore_session():
                if self.carousel.get_width() == 0:
                    return False
                self.carousel.scroll_to(target_editor, False)
                target_editor.textview.grab_focus()
                buffer = target_editor.buffer
                buffer.place_cursor(buffer.get_end_iter())
                
                def reveal():
                    self.carousel.set_opacity(1)
                    return False
                GLib.idle_add(reveal)
                
                self.update_title()
                
                last_seen = config.get("last_seen_version", "0.0.0")
                latest_version, releases_list = self._get_latest_release_info(last_seen=last_seen, as_list=True)
                
                if latest_version != "Unknown" and latest_version != last_seen:
                    config.set("last_seen_version", latest_version)
                    if not is_first_run and releases_list:
                        ChangelogWindow(latest_version, releases_list, parent=self).present(self)
                        
                return False
            
            if not skip_restore:
                GLib.idle_add(restore_session)
                GLib.timeout_add(50, restore_session)
                GLib.timeout_add(200, restore_session)
                GLib.timeout_add(500, restore_session)

    def add_note(self, file_path=None, grab_focus=True, index=None):
        editor = NoteEditor(file_path=file_path, on_title_changed=self.on_editor_title_changed)
        editor.window = self
        if index is not None:
            self.carousel.insert(editor, index)
        else:
            self.carousel.append(editor)
        if grab_focus:
            def grab_it():
                self.carousel.scroll_to(editor, False)
                editor.textview.grab_focus()
                self.update_title()
                return False
            GLib.idle_add(grab_it)
            GLib.timeout_add(50, grab_it)
            GLib.timeout_add(150, grab_it)
        self.update_line_spacing()
        return editor

    def on_carousel_position_notify(self, carousel, param):
        pos = carousel.get_position()
        if pos == int(pos):
            self.cleanup_abandoned_empty_notes(int(pos))
            
    def cleanup_abandoned_empty_notes(self, current_idx):
        n_pages = self.carousel.get_n_pages()
        for i in range(n_pages - 2, current_idx, -1):
            editor = self.carousel.get_nth_page(i)
            if editor.is_empty():
                try:
                    if editor.file_path.exists():
                        editor.file_path.unlink()
                except:
                    pass
                self.carousel.remove(editor)

    def ensure_empty_note_at_end(self):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            self.add_note(grab_focus=False)
            return
            
        last_editor = self.carousel.get_nth_page(n_pages - 1)
        if not last_editor.is_empty():
            self.add_note(grab_focus=False)

    def on_nav_first(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages > 0:
            self.carousel.scroll_to(self.carousel.get_nth_page(0), True)

    def on_nav_last(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages > 0:
            self.carousel.scroll_to(self.carousel.get_nth_page(n_pages - 1), True)

    def on_copy_note(self, action=None, param=None):
        editor = self.get_current_editor()
        if editor:
            start, end = editor.buffer.get_bounds()
            text = editor.buffer.get_text(start, end, True)
            from gi.repository import GObject
            editor.textview.get_clipboard().set(text)
            self.toast_overlay.add_toast(Adw.Toast.new("Note Copied"))

    def on_bump_note(self, action=None, param=None):
        editor = self.get_current_editor()
        if editor and editor.file_path.exists():
            import os
            import time
            os.utime(editor.file_path, None)
            
            is_pinned = self.metadata.get(editor.file_path.name, {}).get("pinned", False)
            if not is_pinned:
                self.carousel.remove(editor)
                target_pos = self.carousel.get_n_pages() - 1 
                self.carousel.insert(editor, target_pos)
                
                def animate_bump():
                    self.carousel.scroll_to(editor, True)
                    editor.textview.grab_focus()
                    return False
                
                GLib.idle_add(animate_bump)
                GLib.timeout_add(50, animate_bump)
                    
            self.toast_overlay.add_toast(Adw.Toast.new("Note moved to front"))

    def on_new_note(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages > 0:
            self.carousel.scroll_to(self.carousel.get_nth_page(n_pages - 1), True)

    def on_undo_delete(self, action=None, param=None):
        if not self.last_deleted_file:
            return
            
        trash_path = TRASH_DIR / self.last_deleted_file
        data_path = DATA_DIR / self.last_deleted_file
        
        if trash_path.exists():
            shutil.move(str(trash_path), str(data_path))
            idx = getattr(self, 'last_deleted_index', None)
            self.add_note(data_path, grab_focus=True, index=idx)
            self.last_deleted_file = None
            self.last_deleted_index = None

    def on_delete_note(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            return

        current_page_idx = int(round(self.carousel.get_position()))
        editor = self.carousel.get_nth_page(current_page_idx)

        # Don't allow deleting an already empty note (prevents app locking bug)
        if editor.is_empty():
            return

        # Skip confirmation if user disabled it
        if not config.get("confirm_delete", True):
            self.perform_delete(editor)
            return

        title = editor.get_title()
        dialog = Adw.AlertDialog(
            heading="Delete Note?",
            body=f"“{title}” will be moved to the trash. You can undo this with Ctrl+Shift+T.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self.on_delete_dialog_response, editor)
        dialog.present(self)

    def on_delete_dialog_response(self, dialog, response, editor):
        if response == "delete":
            self.perform_delete(editor)

    def perform_delete(self, editor):
        # Cancel any pending save timeout to prevent a "ghost note" from writing itself to disk after deletion
        if hasattr(editor, 'save_timeout_id') and editor.save_timeout_id:
            GLib.source_remove(editor.save_timeout_id)
            editor.save_timeout_id = 0

        # Find index to allow restoring to the exact same position
        idx = -1
        for i in range(self.carousel.get_n_pages()):
            if self.carousel.get_nth_page(i) == editor:
                idx = i
                break
        self.last_deleted_index = idx if idx != -1 else None

        toast_msg = "Note deleted"
        if editor.file_path.exists():
            try:
                TRASH_DIR.mkdir(parents=True, exist_ok=True)
                dest_path = TRASH_DIR / editor.file_path.name
                
                # shutil.move crashes if the destination file already exists
                if dest_path.exists():
                    dest_path.unlink()
                    
                # Try to move to trash first
                shutil.move(str(editor.file_path), str(dest_path))
                self.last_deleted_file = editor.file_path.name
            except Exception as e:
                # Fallback
                try:
                    editor.file_path.unlink(missing_ok=True)
                    self.last_deleted_file = None
                    toast_msg = f"Permanent delete fallback (Error: {str(e)})"
                except Exception as e2:
                    toast_msg = f"Failed to delete completely: {e2}"
        else:
            # Note was never saved to disk
            self.last_deleted_file = None

        if hasattr(self, 'current_toast') and self.current_toast:
            self.current_toast.dismiss()

        self.current_toast = Adw.Toast.new(toast_msg)
        if self.last_deleted_file:
            self.current_toast.set_button_label("Undo")
            self.current_toast.set_action_name("win.undo-delete")
        self.current_toast.set_timeout(5)
        self.toast_overlay.add_toast(self.current_toast)

        self.carousel.remove(editor)

        if self.carousel.get_n_pages() == 0:
            self.add_note()
        else:
            self.update_title()

    def on_page_changed(self, carousel, index):
        self.update_title()
        editor = carousel.get_nth_page(int(round(index)))
        if editor:
            fname = editor.file_path.name
            is_pinned = self.metadata.get(fname, {}).get("pinned", False)
            self._ignore_pin_toggle = True
            self.pin_btn.set_active(is_pinned)
            self._ignore_pin_toggle = False
            
            scope = config.get("wysiwyg_scope", "global")
            if scope == "per_note":
                is_wysiwyg = self.metadata.get(fname, {}).get("wysiwyg", False)
                self._ignore_wysiwyg_toggle = True
                self.wysiwyg_btn.set_active(is_wysiwyg)
                self._ignore_wysiwyg_toggle = False
            
            if self.popover.get_visible():
                editor.set_search_highlight(self.search_entry.get_text())
            else:
                GLib.idle_add(lambda: [editor.textview.grab_focus(), False][-1])

    def on_editor_title_changed(self, editor):
        self.ensure_empty_note_at_end()
        if self.carousel.get_n_pages() == 0:
            return
        current_page_idx = int(round(self.carousel.get_position()))
        if current_page_idx < self.carousel.get_n_pages():
            current_editor = self.carousel.get_nth_page(current_page_idx)
            if editor == current_editor:
                self.update_title()

    def update_title(self):
        pass

    def get_current_editor(self):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            return None
        idx = int(round(self.carousel.get_position()))
        idx = max(0, min(idx, n_pages - 1))
        return self.carousel.get_nth_page(idx)

    def on_search_shortcut(self, action, param):
        self.popover.popup()

    def on_popover_visible(self, popover, param):
        if popover.get_visible():
            self.search_entry.set_text("")
            self.populate_note_list()
            self.search_entry.grab_focus()
        else:
            if self.search_timeout_id:
                GLib.source_remove(self.search_timeout_id)
                self.search_timeout_id = 0
            for i in range(self.carousel.get_n_pages()):
                self.carousel.get_nth_page(i).set_search_highlight("")
            editor = self.get_current_editor()
            if editor:
                editor.textview.grab_focus()

    def _build_snippet_markup(self, content, idx, search_text):
        # Asymmetric context: keep the match near the start of the snippet so
        # the highlight stays visible before the label ellipsizes at the end.
        pre, post = 12, 60
        start = max(0, idx - pre)
        end = min(len(content), idx + len(search_text) + post)
        match_offset = idx - start

        snippet = content[start:end]
        before = re.sub(r'\s+', ' ', snippet[:match_offset])
        matched = re.sub(r'\s+', ' ', snippet[match_offset:match_offset + len(search_text)])
        after = re.sub(r'\s+', ' ', snippet[match_offset + len(search_text):])

        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(content) else ""

        return (
            GLib.markup_escape_text(prefix + before)
            + '<span background="#f9f06b" color="#000000">'
            + GLib.markup_escape_text(matched)
            + '</span>'
            + GLib.markup_escape_text(after + suffix)
        )

    def _load_note(self, f):
        # Parse + lowercase once per note, reused until its mtime changes.
        try:
            mtime = os.path.getmtime(f)
        except OSError:
            return None
        cached = self._note_cache.get(f)
        if cached is not None and cached["mtime"] == mtime:
            return cached
        try:
            content = f.read_text(encoding='utf-8')
        except OSError:
            return None
        first_line = content.split('\n', 1)[0].strip()
        title = re.sub(r'^#+\s*', '', first_line) if first_line else "New Note"
        tags = set(re.findall(r'#(\w+)', content))
        entry = {
            "mtime": mtime, "content": content, "low_content": content.lower(),
            "title": title, "tag_str": " ".join(f"#{t}" for t in tags),
            "blank": not content.strip(),
        }
        self._note_cache[f] = entry
        return entry

    def _iter_row_descriptors(self, files, search_text):
        # Lazy: descriptors are pulled by the page renderer, not built up front.
        for f in files:
            entry = self._load_note(f)
            if entry is None or entry["blank"]:
                continue
            title, tag_str, content = entry["title"], entry["tag_str"], entry["content"]
            if not search_text:
                yield {"file": f, "plain": True, "title": title, "tag_str": tag_str}
                continue
            if search_text not in entry["low_content"]:
                continue
            n = 0
            for idx in iter_body_match_offsets(content, search_text, entry["low_content"]):
                yield {
                    "file": f, "content": content, "idx": idx, "occurrence": n,
                    "search": search_text,
                    "title": title if n == 0 else None,
                    "tag_str": tag_str if n == 0 else None,
                }
                n += 1
            if n == 0:
                # Match only in the title/tags line, not the body.
                yield {"file": f, "plain": True, "title": title, "tag_str": tag_str}

    def populate_note_list(self, search_text=""):
        # Clear existing rows
        while child := self.note_listbox.get_first_child():
            self.note_listbox.remove(child)

        search_text = search_text.lower()
        files = sorted(DATA_DIR.glob("*.md"), key=lambda f: os.path.getmtime(f) if f.exists() else 0, reverse=True)
        # Realise widgets one page at a time to keep the UI responsive.
        self._row_iter = self._iter_row_descriptors(files, search_text)
        self._render_next_page()

    def _render_next_page(self):
        if self._row_iter is None:
            return
        count = 0
        for d in self._row_iter:
            self.note_listbox.append(self._row_from_descriptor(d))
            count += 1
            if count >= self.PAGE_SIZE:
                return
        self._row_iter = None  # exhausted

    def _row_from_descriptor(self, d):
        if d.get("plain"):
            row = self._make_note_row(d["file"])
            self._append_header(row.get_child(), d["title"], d["tag_str"])
            return row
        return self._make_snippet_row(
            d["file"], d["content"], d["idx"], d["occurrence"], d["search"],
            title=d["title"], tag_str=d["tag_str"],
        )

    def _append_header(self, vbox, title, tag_str):
        title_label = Gtk.Label(label=title, xalign=0)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.set_max_width_chars(32)
        vbox.append(title_label)
        if tag_str:
            tag_label = Gtk.Label(label=tag_str, xalign=0)
            tag_label.add_css_class("dim-label")
            tag_label.set_ellipsize(Pango.EllipsizeMode.END)
            tag_label.set_max_width_chars(32)
            vbox.append(tag_label)

    def _make_note_row(self, file_path, indent=False):
        row = Gtk.ListBoxRow()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_start(28 if indent else 12)
        vbox.set_margin_end(12)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        row.set_child(vbox)
        row.file_path = file_path
        row.match_index = None
        row.match_term = ""
        return row

    def _make_snippet_row(self, f, content, idx, occurrence_index, search_text, title=None, tag_str=None):
        # title/tag_str only on a note's first match; the rest are indented.
        row = self._make_note_row(f, indent=title is None)
        vbox = row.get_child()
        if title is not None:
            self._append_header(vbox, title, tag_str)

        snippet_label = Gtk.Label(xalign=0)
        snippet_label.set_markup(self._build_snippet_markup(content, idx, search_text))
        snippet_label.add_css_class("dim-label")
        snippet_label.set_ellipsize(Pango.EllipsizeMode.END)
        snippet_label.set_max_width_chars(32)
        snippet_label.set_wrap(False)
        vbox.append(snippet_label)

        # Navigate by occurrence index (the buffer can differ from disk).
        row.match_index = occurrence_index
        row.match_term = search_text
        return row

    def on_search_edge_reached(self, scrolled, pos):
        # Backstop in case a fast scroll outruns the prefetch.
        if pos == Gtk.PositionType.BOTTOM:
            self._render_next_page()

    def on_search_scrolled(self, vadj):
        # Prefetch a screenful early so loading stays invisible.
        if self._row_iter is None:
            return
        remaining_below = vadj.get_upper() - (vadj.get_value() + vadj.get_page_size())
        if remaining_below < vadj.get_page_size():
            self._render_next_page()

    def on_search_changed(self, entry):
        # Debounce: each search rereads every note and rebuilds the list.
        if self.search_timeout_id:
            GLib.source_remove(self.search_timeout_id)
        self.search_timeout_id = GLib.timeout_add(150, self._run_search, entry.get_text())

    def _run_search(self, text):
        self.search_timeout_id = 0
        self.populate_note_list(text)
        editor = self.get_current_editor()
        if editor:
            editor.set_search_highlight(text)
        return False

    def on_note_row_activated(self, listbox, row):
        file_path = getattr(row, 'file_path', None)
        if file_path:
            # Check if it's already in the carousel
            target = None
            for i in range(self.carousel.get_n_pages()):
                editor = self.carousel.get_nth_page(i)
                if editor.file_path == file_path:
                    self.carousel.scroll_to(editor, True)
                    target = editor
                    break

            if target is None:
                target = self.add_note(file_path)

            match_index = getattr(row, 'match_index', None)
            if match_index is not None:
                target.scroll_to_match(getattr(row, 'match_term', ''), match_index)

            self.update_title()
        self.popover.popdown()

    def on_preferences(self, action, param):
        pref_window = Adw.PreferencesDialog()
        
        # --- Appearance Page ---
        appearance_page = Adw.PreferencesPage(title="Appearance", icon_name="preferences-desktop-appearance-symbolic")
        
        # Appearance Group
        font_group = Adw.PreferencesGroup(title="Text")
        font_row = Adw.ActionRow(title="Editor Font")
        
        font_dialog = Gtk.FontDialog()
        font_btn = Gtk.FontDialogButton()
        font_btn.set_dialog(font_dialog)
        font_btn.set_valign(Gtk.Align.CENTER)
        
        font_name = config.get("font_name")
        if font_name:
            font_desc = Pango.FontDescription.from_string(font_name)
            font_btn.set_font_desc(font_desc)
            
        font_btn.connect("notify::font-desc", self.on_font_changed)
        font_row.add_suffix(font_btn)
        font_group.add(font_row)
        
        # Theme Snippets Group
        theme_group = Adw.PreferencesGroup(title="Paper Theme")
        
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_max_children_per_line(3)
        flowbox.set_min_children_per_line(1)
        flowbox.set_row_spacing(12)
        flowbox.set_column_spacing(12)
        flowbox.set_margin_top(8)
        flowbox.set_margin_bottom(8)
        
        themes = ["blank", "dotted", "grid", "large_grid"]
        current_theme = config.get("paper_theme", "blank")
        
        group = None
        for t in themes:
            snippet = ThemeSnippet(t, group=group)
            if group is None:
                group = snippet
            if t == current_theme:
                snippet.set_active(True)
                
            snippet.connect("toggled", self.on_theme_snippet_toggled)
            flowbox.append(snippet)
            
        theme_group.add(flowbox)
        appearance_page.add(theme_group)
        
        # Line Spacing
        spacing_row = Adw.ActionRow(title="Line Spacing")
        spacing_model = Gtk.StringList.new(["1.0", "1.2", "1.5", "2.0"])
        spacing_dropdown = Gtk.DropDown(model=spacing_model)
        spacing_dropdown.set_valign(Gtk.Align.CENTER)
        
        current_spacing = config.get("line_spacing", "1.2")
        try:
            idx = ["1.0", "1.2", "1.5", "2.0"].index(current_spacing)
            spacing_dropdown.set_selected(idx)
        except ValueError:
            pass
            
        spacing_dropdown.connect("notify::selected-item", self.on_spacing_changed)
        spacing_row.add_suffix(spacing_dropdown)
        font_group.add(spacing_row)
        
        appearance_page.add(font_group)
        pref_window.add(appearance_page)

        # --- Behavior Page ---
        behavior_page = Adw.PreferencesPage(title="Behavior", icon_name="preferences-system-symbolic")

        # Behavior Group
        behavior_group = Adw.PreferencesGroup(title="Workflow")
        
        wysiwyg_scope_row = Adw.ActionRow(
            title="WYSIWYG Scope",
            subtitle="Apply Live Formatting globally to all notes, or remember it per note."
        )
        wysiwyg_scope_model = Gtk.StringList.new(["Global", "Per Note"])
        wysiwyg_scope_dropdown = Gtk.DropDown(model=wysiwyg_scope_model)
        wysiwyg_scope_dropdown.set_valign(Gtk.Align.CENTER)
        
        current_scope = config.get("wysiwyg_scope", "global")
        idx = 1 if current_scope == "per_note" else 0
        wysiwyg_scope_dropdown.set_selected(idx)
        
        wysiwyg_scope_dropdown.connect("notify::selected-item", self.on_wysiwyg_scope_changed)
        wysiwyg_scope_row.add_suffix(wysiwyg_scope_dropdown)
        behavior_group.add(wysiwyg_scope_row)
        
        startup_row = Adw.ActionRow(title="Startup Behavior")
        startup_model = Gtk.StringList.new(["Restore last active note", "Start with empty note"])
        startup_dropdown = Gtk.DropDown(model=startup_model)
        startup_dropdown.set_valign(Gtk.Align.CENTER)
        
        current_startup = config.get("startup_behavior", "last_note")
        idx = 1 if current_startup == "empty_note" else 0
        startup_dropdown.set_selected(idx)
        
        startup_dropdown.connect("notify::selected-item", self.on_startup_behavior_changed)
        startup_row.add_suffix(startup_dropdown)
        behavior_group.add(startup_row)

        archive_row = Adw.ActionRow(
            title="Auto-Archive Inactive Notes",
            subtitle="Notes are not deleted. They are simply hidden from the app to reduce clutter, but remain fully searchable via Ctrl+F.",
        )
        archive_model = Gtk.StringList.new(["Never", "1 Week", "1 Month", "1 Year"])
        archive_dropdown = Gtk.DropDown(model=archive_model)
        archive_dropdown.set_valign(Gtk.Align.CENTER)
        
        current_archive = config.get("archive_days", 0)
        idx = 0
        if current_archive == 7:
            idx = 1
        elif current_archive == 30:
            idx = 2
        elif current_archive == 365:
            idx = 3
            
        archive_dropdown.set_selected(idx)
        archive_dropdown.connect("notify::selected-item", self.on_archive_days_changed)
        archive_row.add_suffix(archive_dropdown)
        behavior_group.add(archive_row)

        carousel_size_row = Adw.ActionRow(
            title="Max Carousel Size",
            subtitle="Limit the number of notes loaded into the swipable carousel. Older notes remain fully searchable.",
        )
        carousel_size_model = Gtk.StringList.new(["10 Notes", "25 Notes", "50 Notes", "Unlimited"])
        carousel_size_dropdown = Gtk.DropDown(model=carousel_size_model)
        carousel_size_dropdown.set_valign(Gtk.Align.CENTER)
        
        current_size = config.get("max_carousel_size", 10)
        idx = 0
        if current_size == 25:
            idx = 1
        elif current_size == 50:
            idx = 2
        elif current_size == 0:
            idx = 3
            
        carousel_size_dropdown.set_selected(idx)
        carousel_size_dropdown.connect("notify::selected-item", self.on_carousel_size_changed)
        carousel_size_row.add_suffix(carousel_size_dropdown)
        behavior_group.add(carousel_size_row)

        confirm_row = Adw.ActionRow(
            title="Confirm Before Deleting",
            subtitle="Ask for confirmation when deleting a note",
        )
        confirm_switch = Gtk.Switch()
        confirm_switch.set_valign(Gtk.Align.CENTER)
        confirm_switch.set_active(config.get("confirm_delete", True))
        confirm_switch.connect("notify::active", self.on_confirm_delete_changed)
        confirm_row.add_suffix(confirm_switch)
        confirm_row.set_activatable_widget(confirm_switch)
        behavior_group.add(confirm_row)
        
        toast_row = Adw.ActionRow(
            title="Show Command Confirmations",
            subtitle="Display a small confirmation message when you use a text manipulation command",
        )
        toast_switch = Gtk.Switch()
        toast_switch.set_valign(Gtk.Align.CENTER)
        toast_switch.set_active(config.get("show_command_toasts", True))
        
        def on_toast_switch_changed(switch, param):
            config.set("show_command_toasts", switch.get_active())
            
        toast_switch.connect("notify::active", on_toast_switch_changed)
        toast_row.add_suffix(toast_switch)
        toast_row.set_activatable_widget(toast_switch)
        behavior_group.add(toast_row)
        
        behavior_page.add(behavior_group)

        # --- Running Group ---
        running_group = Adw.PreferencesGroup(title="Running")

        self.bg_row = Adw.ActionRow(
            title="Keep Running in Background",
            subtitle="Hides the application when closed instead of terminating",
        )
        self.bg_switch = Gtk.Switch()
        self.bg_switch.set_valign(Gtk.Align.CENTER)
        self.bg_switch.set_active(config.get("run_in_background", False))
        self.bg_switch.connect("notify::active", self.on_bg_switch_changed)
        self.bg_row.add_suffix(self.bg_switch)
        self.bg_row.set_activatable_widget(self.bg_switch)
        running_group.add(self.bg_row)

        self.startup_row = Adw.ActionRow(
            title="Run on Startup",
            subtitle="Automatically launch the application when you log in",
        )
        self.startup_switch = Gtk.Switch()
        self.startup_switch.set_valign(Gtk.Align.CENTER)
        self.startup_switch.set_active(config.get("run_on_startup", False))
        self.startup_switch.connect("notify::active", self.on_startup_switch_changed)
        self.startup_row.add_suffix(self.startup_switch)
        self.startup_row.set_activatable_widget(self.startup_switch)
        running_group.add(self.startup_row)

        self.hidden_row = Adw.ActionRow(
            title="Start Hidden",
            subtitle="Launch in the background without opening a window",
        )
        self.hidden_switch = Gtk.Switch()
        self.hidden_switch.set_valign(Gtk.Align.CENTER)
        self.hidden_switch.set_active(config.get("start_hidden", False))
        self.hidden_switch.connect("notify::active", self.on_hidden_switch_changed)
        self.hidden_row.add_suffix(self.hidden_switch)
        self.hidden_row.set_activatable_widget(self.hidden_switch)
        running_group.add(self.hidden_row)

        self._update_hidden_switch_sensitivity()
        behavior_page.add(running_group)
        pref_window.add(behavior_page)

        # --- Storage Page ---
        storage_page = Adw.PreferencesPage(title="Storage", icon_name="drive-harddisk-symbolic")

        # Storage Group
        storage_group = Adw.PreferencesGroup(title="Data Location")
        
        row = Adw.ActionRow(title="Notes Directory", subtitle=str(DATA_DIR))
        
        btn = Gtk.Button(label="Change...")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", self.on_change_dir, row)
        row.add_suffix(btn)
        
        storage_group.add(row)
        storage_page.add(storage_group)
        
        pref_window.add(storage_page)
        pref_window.present(self)

    def _update_hidden_switch_sensitivity(self):
        can_start_hidden = self.bg_switch.get_active() and self.startup_switch.get_active()
        self.hidden_row.set_sensitive(can_start_hidden)
        if not can_start_hidden:
            self.hidden_switch.set_active(False)
            config.set("start_hidden", False)

    def on_bg_switch_changed(self, switch, param):
        is_bg = switch.get_active()
        config.set("run_in_background", is_bg)
        self._update_hidden_switch_sensitivity()
        app = self.get_application()
        if is_bg:
            app.hold()
        else:
            app.release()

    def on_startup_switch_changed(self, switch, param):
        is_active = switch.get_active()
        config.set("run_on_startup", is_active)
        self._update_hidden_switch_sensitivity()

        try:
            from gi.repository import Gio, GLib
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            options = GLib.Variant("a{sv}", {
                "reason": GLib.Variant("s", "Start Whisp in the background"),
                "autostart": GLib.Variant("b", is_active),
                "commandline": GLib.Variant("as", ["whisp", "--hidden"]) if is_active else GLib.Variant("as", [])
            })
            parameters = GLib.Variant.new_tuple(GLib.Variant("s", ""), options)
            
            def on_bg_response(conn, sender, path, iface, signame, params, ud):
                pass
                
            def on_request(source, result, ud):
                try:
                    ret = source.call_finish(result)
                    request_handle = ret.unpack()[0]
                    bus.signal_subscribe(
                        "org.freedesktop.portal.Desktop", "org.freedesktop.portal.Request",
                        "Response", request_handle, None, Gio.DBusSignalFlags.NONE,
                        on_bg_response, None
                    )
                except Exception as e:
                    print("Background request error:", e)

            bus.call(
                "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Background", "RequestBackground",
                parameters, None, Gio.DBusCallFlags.NONE, -1, None,
                on_request, None
            )
        except Exception as e:
            print("Failed to request background portal via DBus:", e)

    def on_hidden_switch_changed(self, switch, param):
        config.set("start_hidden", switch.get_active())

    def on_font_changed(self, font_btn, param):
        desc = font_btn.get_font_desc()
        if desc:
            font_name = desc.to_string()
            config.set("font_name", font_name)
            self.apply_theme()

    def on_theme_snippet_toggled(self, snippet):
        if snippet.get_active():
            old_theme = config.get("paper_theme", "blank")
            theme_id = snippet.theme_id
            config.set("paper_theme", theme_id)
            
            # Update all open editors
            for i in range(self.carousel.get_n_pages()):
                editor = self.carousel.get_nth_page(i)
                editor.textview.remove_css_class(f"paper-{old_theme}")
                editor.textview.add_css_class(f"paper-{theme_id}")

    def on_spacing_changed(self, dropdown, param):
        selected = dropdown.get_selected_item()
        if selected:
            spacing = selected.get_string()
            config.set("line_spacing", spacing)
            self.update_line_spacing()

    def on_confirm_delete_changed(self, switch, param):
        config.set("confirm_delete", switch.get_active())

    def on_startup_behavior_changed(self, dropdown, param):
        selected = dropdown.get_selected()
        val = "empty_note" if selected == 1 else "last_note"
        config.set("startup_behavior", val)

    def on_wysiwyg_scope_changed(self, dropdown, param):
        idx = dropdown.get_selected()
        scope = "per_note" if idx == 1 else "global"
        config.set("wysiwyg_scope", scope)
        
        if scope == "global":
            global_mode = config.get("wysiwyg_mode", False)
            self._ignore_wysiwyg_toggle = True
            self.wysiwyg_btn.set_active(global_mode)
            self._ignore_wysiwyg_toggle = False
        else:
            editor = self.get_current_editor()
            if editor:
                fname = editor.file_path.name
                note_mode = self.metadata.get(fname, {}).get("wysiwyg", False)
                self._ignore_wysiwyg_toggle = True
                self.wysiwyg_btn.set_active(note_mode)
                self._ignore_wysiwyg_toggle = False
                
        for i in range(self.carousel.get_n_pages()):
            editor = self.carousel.get_nth_page(i)
            editor.highlighter.highlight()

    def on_archive_days_changed(self, dropdown, param):
        idx = dropdown.get_selected()
        day_map = {0: 0, 1: 7, 2: 30, 3: 365}
        days = day_map.get(idx, 0)
        config.set("archive_days", days)

    def on_carousel_size_changed(self, dropdown, param):
        idx = dropdown.get_selected()
        size_map = {0: 10, 1: 25, 2: 50, 3: 0}
        size = size_map.get(idx, 10)
        config.set("max_carousel_size", size)

    def update_line_spacing(self):
        spacing_str = config.get("line_spacing", "1.2")
        try:
            spacing_val = float(spacing_str)
        except ValueError:
            spacing_val = 1.2
            
        # Convert multiplier to rough pixels (assuming ~16px font size)
        # Normal (1.0) = 0px
        # Relaxed (1.2) = 3px above/below
        # Loose (1.5) = 8px above/below
        # Very Loose (2.0) = 16px above/below
        extra_pixels = int((spacing_val - 1.0) * 16)
        above_below = max(0, extra_pixels // 2)
        inside_wrap = max(0, extra_pixels)
        
        for i in range(self.carousel.get_n_pages()):
            editor = self.carousel.get_nth_page(i)
            editor.textview.set_pixels_above_lines(above_below)
            editor.textview.set_pixels_below_lines(above_below)
            editor.textview.set_pixels_inside_wrap(inside_wrap)

    def on_change_dir(self, btn, row):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Notes Directory")
        dialog.select_folder(self, None, self.on_folder_selected, row)

    def on_folder_selected(self, dialog, result, row):
        global DATA_DIR, TRASH_DIR
        try:
            folder = dialog.select_folder_finish(result)
            new_dir = Path(folder.get_path())
            if new_dir != DATA_DIR:
                config.data_dir = new_dir
                DATA_DIR = new_dir
                TRASH_DIR = DATA_DIR / ".trash"
                row.set_subtitle(str(DATA_DIR))
                
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                
                # Clear carousel and reload
                while self.carousel.get_n_pages() > 0:
                    self.carousel.remove(self.carousel.get_nth_page(0))
                self.load_notes()
        except GLib.Error:
            pass

    def on_pin_toggled(self, btn):
        self.set_keep_above(btn.get_active())

    def on_close_request(self, window):
        config.set("window_width", self.get_width())
        config.set("window_height", self.get_height())
        config.set("is_maximized", self.is_maximized())
        
        current_page_idx = int(round(self.carousel.get_position()))
        if current_page_idx < self.carousel.get_n_pages():
            editor = self.carousel.get_nth_page(current_page_idx)
            config.set("last_active_note", str(editor.file_path))
            
        return False

    def apply_theme(self):
        font_name = config.get("font_name")
        font_css = ""
        if font_name:
            font_desc = Pango.FontDescription.from_string(font_name)
            family = font_desc.get_family()
            size = font_desc.get_size() / Pango.SCALE
            font_css = f"font-family: '{family}'; font-size: {size}pt;"
            
        custom_css = f"""
        textview {{ {font_css} }}
        
        .theme-btn {{
            min-width: 48px;
            min-height: 48px;
            border-radius: 50%;
            border: 1px solid alpha(currentColor, 0.15);
            padding: 0;
            box-shadow: none;
        }}
        .theme-btn.system {{
            background: linear-gradient(135deg, #ffffff 49.5%, #242424 50.5%);
        }}
        .theme-btn.light {{
            background: #ffffff;
        }}
        .theme-btn.dark {{
            background: #242424;
        }}
        .theme-btn:checked {{
            border: 2px solid @accent_bg_color;
            box-shadow: inset 0 0 0 2px @window_bg_color;
        }}
        """
        try:
            self.css_provider.load_from_data(custom_css.encode('utf-8'))
        except GLib.Error:
            pass
