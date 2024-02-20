# Plugin by Sinan Nalkaya <sardok@gmail.com>
# See LICENSE of Terminator package.

""" logger.py - Terminator Plugin to log 'content' of individual
terminals """

import os
import sys
from gi.repository import Gtk
import terminatorlib.plugin as plugin
from terminatorlib.translation import _

AVAILABLE = ['LoggerUnbuffered']


class LoggerUnbuffered(plugin.MenuItem):

    """ Add custom command to the terminal menu"""
    capabilities = ['terminal_menu']
    loggers = None
    dialog_action = Gtk.FileChooserAction.SAVE
    dialog_buttons = (_("_Cancel"), Gtk.ResponseType.CANCEL,
                      _("_Save"), Gtk.ResponseType.OK)

    def __init__(self):

        plugin.MenuItem.__init__(self)
        if not self.loggers:
            self.loggers = {}

    def callback(self, menuitems, menu, terminal):
        """ Add save menu item to the menu"""
        vte_terminal = terminal.get_vte()
        if vte_terminal not in self.loggers:
            item = Gtk.MenuItem.new_with_mnemonic(_('Start unbuffered logger '))
            item.connect("activate", self.start_logger, terminal)
        else:
            item = Gtk.MenuItem.new_with_mnemonic(_('Stop unbuffered logger '))
            item.connect("activate", self.stop_logger, terminal)
            item.set_has_tooltip(True)
            item.set_tooltip_text("Saving at '" + self.loggers[vte_terminal]["filepath"] + "'")

            item1 = Gtk.MenuItem.new_with_mnemonic(_('Reset unbuffered logger file'))
            item1.connect("activate", self.reset_file, terminal)
            menuitems.append(item1)

            if self.loggers[vte_terminal]["pause"]:
                item2 = Gtk.MenuItem.new_with_mnemonic(_('Resume unbuffered logger file'))
                item2.connect("activate", self.resume_logging, terminal)
                menuitems.append(item2)
            else:
                item2 = Gtk.MenuItem.new_with_mnemonic(_('Pause unbuffered logger file'))
                item2.connect("activate", self.pause_logging, terminal)
                menuitems.append(item2)

        menuitems.append(item)

    def write_content(self, terminal, row_start, col_start, row_end, col_end):
        """ Final function to write a file """
        if self.loggers[terminal]["pause"]:
            self.loggers[terminal]["col"] = col_end
            self.loggers[terminal]["row"] = row_end
            return
        content = terminal.get_text_range(row_start, col_start, row_end, col_end,
                                          lambda *a: True)
        content = content[0]
        if not content or '\n' not in content:
            return

        self.loggers[terminal]["col"] = col_end
        self.loggers[terminal]["row"] = row_end
        fd = self.loggers[terminal]["fd"]
        fd.write(content)

    def save(self, terminal):
        """ 'contents-changed' callback """
        last_saved_col = self.loggers[terminal]["col"]
        last_saved_row = self.loggers[terminal]["row"]
        (col, row) = terminal.get_cursor_position()

        self.write_content(terminal, last_saved_row, last_saved_col, row, col)
        
    def start_logger(self, _widget, Terminal):
        """ Handle menu item callback by saving text to a file"""
        savedialog = Gtk.FileChooserDialog(title=_("Save Log File As"),
                                           action=self.dialog_action,
                                           buttons=self.dialog_buttons)
        savedialog.set_transient_for(_widget.get_toplevel())
        savedialog.set_do_overwrite_confirmation(True)
        savedialog.set_local_only(True)
        savedialog.show_all()
        response = savedialog.run()
        if response == Gtk.ResponseType.OK:
            try:
                logfile = os.path.join(savedialog.get_current_folder(),
                                       savedialog.get_filename())
                fd = open(logfile, 'w+', buffering=1)
                # Save log file path, 
                # associated file descriptor, signal handler id
                # and last saved col,row positions respectively.
                vte_terminal = Terminal.get_vte()
                (col, row) = vte_terminal.get_cursor_position()

                self.loggers[vte_terminal] = {
                                                "filepath": logfile,
                                                "handler_id": 0, "fd": fd,
                                                "col": col, "row": row,
                                                "pause": False
                                              }
                # Add contents-changed callback
                self.loggers[vte_terminal]["handler_id"] = vte_terminal.connect('contents-changed', self.save)

            except:
                e = sys.exc_info()[1]
                error = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                                          Gtk.ButtonsType.OK, e.strerror)
                error.set_transient_for(savedialog)
                error.run()
                error.destroy()
        savedialog.destroy()

    def stop_logger(self, _widget, terminal):
        vte_terminal = terminal.get_vte()
        last_saved_col = self.loggers[vte_terminal]["col"]
        last_saved_row = self.loggers[vte_terminal]["row"]
        (col, row) = vte_terminal.get_cursor_position()
        if last_saved_col != col or last_saved_row != row:
            # Save unwritten bufer to the file
            self.write_content(vte_terminal, last_saved_row, last_saved_col, row, col)
        fd = self.loggers[vte_terminal]["fd"]
        fd.close()
        vte_terminal.disconnect(self.loggers[vte_terminal]["handler_id"])
        del(self.loggers[vte_terminal])

    def reset_file(self, _widget, terminal):
        vte_terminal = terminal.get_vte()
        fd = self.loggers[vte_terminal]["fd"]
        fd.truncate(0)

        self.loggers[vte_terminal]["col"] = 0
        self.loggers[vte_terminal]["row"] = 0

    def pause_logging(self, _widget, terminal):
        vte_terminal = terminal.get_vte()
        self.loggers[vte_terminal]["pause"] = True

    def resume_logging(self, _widget, terminal):
        vte_terminal = terminal.get_vte()
        self.loggers[vte_terminal]["pause"] = False
