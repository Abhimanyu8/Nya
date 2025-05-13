import curses
import sys
import os

class TextEditor:
    def __init__(self, stdscr, filename=None):
        self.stdscr = stdscr
        self.filename = filename
        self.text = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.scroll_y = 0  # Scroll position
        self.status_message = ""
        self.status_timer = 0
        self.modified = False
        self.cat_editor = None  # Will be set by CatEditor
        self.load_file()

    def load_file(self):
        if self.filename:
            try:
                with open(self.filename, 'r') as file:
                    self.text = file.readlines()
                # Strip newlines for display
                self.text = [line.rstrip('\n') for line in self.text]
                self.set_status_message(f"Read file: {self.filename}")
            except FileNotFoundError:
                self.text = [""]
                self.set_status_message(f"New file: {self.filename}")
        else:
            # Start with one empty line if no file is loaded
            self.text = [""]
            self.set_status_message("New buffer")
    
    def save_file(self):
        if not self.filename:
            return False
        
        try:
            with open(self.filename, 'w') as file:
                for line in self.text:
                    file.write(line + '\n')
            self.modified = False
            self.set_status_message(f"Saved: {self.filename}")
            return True
        except Exception as e:
            self.set_status_message(f"Error saving: {str(e)}")
            return False
    
    def set_status_message(self, msg, ttl=5):
        self.status_message = msg
        self.status_timer = ttl
    
    def insert_char(self, ch):
        # Insert a character at cursor position
        if not self.text:
            self.text = [""]
        
        current_line = self.text[self.cursor_y]
        self.text[self.cursor_y] = current_line[:self.cursor_x] + chr(ch) + current_line[self.cursor_x:]
        self.cursor_x += 1
        self.modified = True
    
    def insert_newline(self):
        # Handle Enter key - split line at cursor
        if not self.text:
            self.text = [""]
            
        current_line = self.text[self.cursor_y]
        self.text[self.cursor_y] = current_line[:self.cursor_x]
        self.text.insert(self.cursor_y + 1, current_line[self.cursor_x:])
        self.cursor_y += 1
        self.cursor_x = 0
        self.modified = True
    
    def delete_char(self):
        # Delete character at cursor position
        if not self.text:
            return
            
        current_line = self.text[self.cursor_y]
        if self.cursor_x > 0:
            # Delete character before cursor
            self.text[self.cursor_y] = current_line[:self.cursor_x-1] + current_line[self.cursor_x:]
            self.cursor_x -= 1
            self.modified = True
        elif self.cursor_y > 0:
            # At beginning of line, join with previous line
            prev_line = self.text[self.cursor_y - 1]
            self.cursor_x = len(prev_line)
            self.text[self.cursor_y - 1] = prev_line + current_line
            self.text.pop(self.cursor_y)
            self.cursor_y -= 1
            self.modified = True
    
    def move_cursor(self, key):
        if key == curses.KEY_RIGHT:
            # Move right
            if self.cursor_x < len(self.text[self.cursor_y]):
                self.cursor_x += 1
            elif self.cursor_y < len(self.text) - 1:
                # Move to beginning of next line
                self.cursor_y += 1
                self.cursor_x = 0
                
        elif key == curses.KEY_LEFT:
            # Move left
            if self.cursor_x > 0:
                self.cursor_x -= 1
            elif self.cursor_y > 0:
                # Move to end of previous line
                self.cursor_y -= 1
                self.cursor_x = len(self.text[self.cursor_y])
                
        elif key == curses.KEY_UP:
            # Move up
            if self.cursor_y > 0:
                self.cursor_y -= 1
                # Adjust x position if line is shorter
                self.cursor_x = min(self.cursor_x, len(self.text[self.cursor_y]))
                
        elif key == curses.KEY_DOWN:
            # Move down
            if self.cursor_y < len(self.text) - 1:
                self.cursor_y += 1
                # Adjust x position if line is shorter
                self.cursor_x = min(self.cursor_x, len(self.text[self.cursor_y]))
                
        elif key == curses.KEY_HOME:
            # Move to beginning of line
            self.cursor_x = 0
            
        elif key == curses.KEY_END:
            # Move to end of line
            self.cursor_x = len(self.text[self.cursor_y])
    
    def process_keypress(self, key):
        if key == curses.KEY_RIGHT or key == curses.KEY_LEFT or \
           key == curses.KEY_UP or key == curses.KEY_DOWN or \
           key == curses.KEY_HOME or key == curses.KEY_END:
            self.move_cursor(key)
        elif key == 10 or key == 13:  # Enter key
            self.insert_newline()
        elif key == 127 or key == curses.KEY_BACKSPACE:  # Backspace
            self.delete_char()
        elif key == curses.KEY_DC:  # Delete key
            # TODO: Implement delete key
            pass
        elif key == 24:  # Ctrl+X - exit
            if self.modified:
                self.set_status_message("Save modified buffer? (y/n)", ttl=100)
                self.stdscr.refresh()
                confirm = self.stdscr.getch()

                if confirm in (ord('y'), ord('Y')):
                    if not self.save_file():
                        return True  # Don't exit if save failed
                elif confirm not in (ord('n'), ord('N')):
                    self.set_status_message("Cancelled exit")
                    return True  # Don't exit
            return False  # Exit the editor
        elif key == 19:  # Ctrl+S - save
            self.save_file()
        elif 32 <= key <= 126:  # Printable ASCII
            self.insert_char(key)
            
        # Ensure cursor is always within bounds
        if self.cursor_y >= len(self.text):
            self.cursor_y = len(self.text) - 1
        if self.cursor_x > len(self.text[self.cursor_y]):
            self.cursor_x = len(self.text[self.cursor_y])
            
        # Update scroll position to keep cursor visible
        self.scroll_if_needed()
        return True
    
    def scroll_if_needed(self):
        # Determine visible area
        editor_start_row = self.cat_editor.cat_head_height if hasattr(self, 'cat_editor') else 3
        editor_height = self.cat_editor.calculate_editor_space() if hasattr(self, 'cat_editor') else 10
        
        # Scroll down if cursor below visible area
        if self.cursor_y - self.scroll_y >= editor_height:
            self.scroll_y = self.cursor_y - editor_height + 1
            
        # Scroll up if cursor above visible area
        if self.cursor_y < self.scroll_y:
            self.scroll_y = self.cursor_y

    def draw_status_bar(self, row):
        # Draw status bar with filename, modified status, cursor position
        height, width = self.stdscr.getmaxyx()
        status = f" {self.filename or 'Untitled'} "
        status += "* " if self.modified else "  "
        status += f"| Line {self.cursor_y+1}/{len(self.text)} | Col {self.cursor_x+1} "
        
        try:
            self.stdscr.attron(curses.A_REVERSE)
            self.stdscr.addstr(row, 0, status.ljust(width-1))
            self.stdscr.attroff(curses.A_REVERSE)
            
            # Draw message line
            if self.status_timer > 0:
                self.status_timer -= 1
                self.stdscr.addstr(row+1, 0, self.status_message[:width-1].ljust(width-1))
            else:
                self.stdscr.addstr(row+1, 0, " " * (width-1))
        except curses.error:
            pass
    
    def draw(self, start_row, end_row):
        height, width = self.stdscr.getmaxyx()
        # Calculate visible range
        editor_height = end_row - start_row
        
        # Draw text content
        for i in range(editor_height):
            file_row = i + self.scroll_y
            line_num = start_row + i
            
            if file_row >= len(self.text):
                # Clear rest of editor area
                if line_num < height:
                    try:
                        self.stdscr.addstr(line_num, 0, " " * (width-1))
                    except curses.error:
                        pass
                continue
            
            line = self.text[file_row]
            if line_num < height:
                try:
                    # Print the line
                    self.stdscr.addstr(line_num, 0, line[:width-1])
                    # Clear rest of line
                    if len(line) < width-1:
                        self.stdscr.addstr(line_num, len(line), " " * (width-1-len(line)))
                except curses.error:
                    pass
        
        # Draw status bar at the end of editor area
        self.draw_status_bar(end_row - 2)
        
        # Position cursor
        cursor_screen_y = start_row + (self.cursor_y - self.scroll_y)
        try:
            self.stdscr.move(cursor_screen_y, self.cursor_x)
        except curses.error:
            pass


class CatEditor:
    def __init__(self, stdscr, filename=None):
        self.stdscr = stdscr
        self.filename = filename
        self.editor = TextEditor(stdscr, filename)
        self.editor.cat_editor = self  # Set back-reference
        self.running = True
        self.min_editor_lines = 5  # Minimum editor space (when file is small)
        self.cat_head_height = 3   # Cat head + paws
        self.cat_bottom_height = 4 # Cat bottom parts

    def calculate_editor_space(self):
        """Calculate the ideal editor space based on file length and screen size"""
        height, width = self.stdscr.getmaxyx()
        
        # Available space for editor (excluding status bar and help line)
        max_available = height - self.cat_head_height - self.cat_bottom_height - 1
        
        # Calculate desired space based on file length (add buffer of 5 lines)
        desired_lines = len(self.editor.text) + 5
        
        # Use the smaller of desired space or max available
        editor_lines = min(desired_lines, max_available)
        
        # But never less than minimum editor lines
        return max(editor_lines, self.min_editor_lines)

    def draw_cat(self):
        height, width = self.stdscr.getmaxyx()

        # Ensure the screen is big enough
        if height < 10 or width < 50:
            self.stdscr.addstr(0, 0, "Terminal too small. Please resize.")
            self.stdscr.refresh()
            return False

        # ** Cat head (centered) **
        cat_head = [
            "  ∧＿∧  ",
            " ( ･ω･) ",
        ]
        head_width = max(len(line) for line in cat_head)
        head_start_col = (width - head_width) // 2

        for i, line in enumerate(cat_head):
            row = i
            if row < height:
                try:
                    self.stdscr.addstr(row, head_start_col, line[:width - head_start_col])
                except curses.error:
                    pass

        # ** Cat paws line (centered) **
        core_paw = "∪――――∪―"
        left_pad = (width - len(core_paw)) // 2
        right_pad = width - len(core_paw) - left_pad
        paw_line = "―" * left_pad + core_paw + "―" * right_pad

        paw_row = len(cat_head)
        if paw_row < height:
            try:
                self.stdscr.addstr(paw_row, 0, paw_line[:width-1])
            except curses.error:
                pass

        # Calculate dynamic editor space
        editor_lines = self.calculate_editor_space()
        
        # ** Editor space **
        editor_start_row = self.cat_head_height
        editor_end_row = editor_start_row + editor_lines
        
        # Ensure we don't go past screen bounds
        if editor_end_row >= height - self.cat_bottom_height:
            editor_end_row = height - self.cat_bottom_height
            
        self.editor.draw(editor_start_row, editor_end_row)

        # ** Bottom part (body + feet) **
        body_core = "________"
        left_pad = (width - len(body_core)) // 2
        right_pad = width - len(body_core) - left_pad
        body_line = "_" * left_pad + body_core + "_" * right_pad

        cat_bottom = [
            body_line,
            " |    | ",
            " |    | ",
            "  U  U  ",
        ]
        bottom_start_row = editor_end_row
        for i, line in enumerate(cat_bottom):
            row = bottom_start_row + i
            if 0 <= row < height:
                if i == 0:
                    # Draw the body line extended to screen edges
                    try:
                        self.stdscr.addstr(row, 0, line[:width-1])
                    except curses.error:
                        pass
                else:
                    # Center the rest (feet)
                    col = (width - len(line)) // 2
                    try:
                        self.stdscr.addstr(row, col, line[:width-col-1])
                    except curses.error:
                        pass
        
        return True

    def draw_help(self):
        height, width = self.stdscr.getmaxyx()
        help_row = height - 1
        help_text = " ^X: Exit | ^S: Save | arrows: Move | ^G: Help"
        
        try:
            self.stdscr.attron(curses.A_REVERSE)
            self.stdscr.addstr(help_row, 0, help_text[:width-1].ljust(width-1))
            self.stdscr.attroff(curses.A_REVERSE)
        except curses.error:
            pass

    def run(self):
        while self.running:
            # Clear screen
            self.stdscr.clear()
            
            # Draw cat and editor
            if not self.draw_cat():
                continue
                
            # Draw help bar
            self.draw_help()
            
            # Refresh the screen
            self.stdscr.refresh()
            
            # Handle input
            try:
                key = self.stdscr.getch()
                
                if key == ord('q') or key == 17:  # 'q' or Ctrl+Q to quit
                    if self.editor.modified:
                        self.editor.set_status_message("Modified buffer exists! Use Ctrl+X to exit")
                    else:
                        self.running = False
                elif key == 24:  # Ctrl+X - exit process
                    if self.editor.modified:
                        self.editor.set_status_message("Save modified buffer? (Y/n)")
                        ch = self.stdscr.getch()
                        if ch == ord('y') or ch == ord('Y') or ch == 10:  # Y or Enter
                            if self.editor.save_file():
                                self.running = False
                        elif ch == ord('n') or ch == ord('N'):
                            self.running = False
                    else:
                        self.running = False
                else:
                    # Pass to editor for processing
                    self.editor.process_keypress(key)
                    
            except KeyboardInterrupt:
                break


def main(stdscr, filename=None):
    # Setup terminal
    curses.start_color()
    curses.use_default_colors()
    curses.curs_set(1)  # Show cursor for text editing
    curses.raw()  # Get control characters
    
    # Create editor and run
    cat_editor = CatEditor(stdscr, filename)
    cat_editor.run()


if __name__ == "__main__":
    curses.wrapper(main, sys.argv[1] if len(sys.argv) > 1 else None)