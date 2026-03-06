"""OrganizerGUI - Tkinter-based graphical interface for Smart File Organizer."""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Optional

from organizer.file_organizer import FileOrganizer


class OrganizerGUI:
    """A tkinter GUI for the Smart File Organizer.

    Provides folder selection, organize/stop buttons, undo functionality,
    a preview panel, and a real-time progress/log display.
    """

    WINDOW_TITLE = "Smart File Organizer"
    WINDOW_MIN_WIDTH = 750
    WINDOW_MIN_HEIGHT = 580
    PAD = 10

    def __init__(self, organizer: Optional[FileOrganizer] = None) -> None:
        """Initialize the GUI.

        Args:
            organizer: An existing FileOrganizer instance. Creates one if None.
        """
        self._organizer = organizer or FileOrganizer()
        self._root: Optional[tk.Tk] = None
        self._selected_folder: Optional[Path] = None
        self._organize_thread: Optional[threading.Thread] = None

        # Widget references (set during run / _build_ui)
        self._folder_var: Optional[tk.StringVar] = None
        self._status_var: Optional[tk.StringVar] = None
        self._progress_var: Optional[tk.DoubleVar] = None
        self._log_text: Optional[tk.Text] = None
        self._preview_tree: Optional[ttk.Treeview] = None
        self._btn_organize: Optional[ttk.Button] = None
        self._btn_stop: Optional[ttk.Button] = None
        self._btn_undo: Optional[ttk.Button] = None
        self._btn_undo_all: Optional[ttk.Button] = None
        self._progress_bar: Optional[ttk.Progressbar] = None

    def run(self) -> None:
        """Launch the GUI application."""
        self._root = tk.Tk()
        self._root.title(self.WINDOW_TITLE)
        self._root.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)

        # Create Tk variables now that the root window exists
        self._folder_var = tk.StringVar()
        self._status_var = tk.StringVar(value="Ready")
        self._progress_var = tk.DoubleVar(value=0.0)
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(2, weight=1)

        self._apply_style()
        self._build_ui()

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    def _apply_style(self) -> None:
        """Configure ttk styles for a clean modern look."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Title.TLabel", font=("Helvetica", 16, "bold"))
        style.configure("Status.TLabel", font=("Helvetica", 10))
        style.configure("TButton", padding=(10, 5))
        style.configure(
            "Organize.TButton", foreground="white", background="#2ecc71",
            font=("Helvetica", 10, "bold"),
        )
        style.map(
            "Organize.TButton",
            background=[("active", "#27ae60"), ("disabled", "#bdc3c7")],
        )
        style.configure(
            "Stop.TButton", foreground="white", background="#e74c3c",
            font=("Helvetica", 10, "bold"),
        )
        style.map(
            "Stop.TButton",
            background=[("active", "#c0392b"), ("disabled", "#bdc3c7")],
        )

    def _build_ui(self) -> None:
        """Construct all UI widgets."""
        self._build_top_bar()
        self._build_action_bar()
        self._build_main_area()
        self._build_status_bar()

    # ── Top bar: folder selection ──────────────────────────────────────

    def _build_top_bar(self) -> None:
        """Build the folder selection bar at the top."""
        frame = ttk.Frame(self._root, padding=self.PAD)
        frame.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Smart File Organizer", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        ttk.Label(frame, text="Folder:").grid(row=1, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(frame, textvariable=self._folder_var, state="readonly").grid(
            row=1, column=1, sticky="ew", padx=5
        )
        ttk.Button(frame, text="Browse…", command=self._browse_folder).grid(
            row=1, column=2, sticky="e"
        )

    # ── Action bar: buttons ────────────────────────────────────────────

    def _build_action_bar(self) -> None:
        """Build the action buttons row."""
        frame = ttk.Frame(self._root, padding=(self.PAD, 0, self.PAD, 5))
        frame.grid(row=1, column=0, sticky="ew")

        self._btn_organize = ttk.Button(
            frame, text="▶  Organize", style="Organize.TButton",
            command=self._start_organize, state="disabled",
        )
        self._btn_organize.pack(side="left", padx=(0, 5))

        self._btn_stop = ttk.Button(
            frame, text="■  Stop", style="Stop.TButton",
            command=self._stop_organize, state="disabled",
        )
        self._btn_stop.pack(side="left", padx=5)

        ttk.Button(
            frame, text="Preview", command=self._show_preview,
        ).pack(side="left", padx=5)

        ttk.Separator(frame, orient="vertical").pack(side="left", fill="y", padx=10)

        self._btn_undo = ttk.Button(
            frame, text="↩ Undo Last", command=self._undo_last, state="disabled",
        )
        self._btn_undo.pack(side="left", padx=5)

        self._btn_undo_all = ttk.Button(
            frame, text="↩ Undo All", command=self._undo_all, state="disabled",
        )
        self._btn_undo_all.pack(side="left", padx=5)

    # ── Main area: preview tree + log ──────────────────────────────────

    def _build_main_area(self) -> None:
        """Build the main content area with preview tree and log pane."""
        paned = ttk.PanedWindow(self._root, orient="horizontal")
        paned.grid(row=2, column=0, sticky="nsew", padx=self.PAD, pady=5)

        # Left: preview treeview
        preview_frame = ttk.LabelFrame(paned, text="Preview", padding=5)
        self._preview_tree = ttk.Treeview(
            preview_frame, columns=("count",), show="tree headings", selectmode="none"
        )
        self._preview_tree.heading("#0", text="Category / File", anchor="w")
        self._preview_tree.heading("count", text="Count", anchor="center")
        self._preview_tree.column("#0", width=250, stretch=True)
        self._preview_tree.column("count", width=60, stretch=False, anchor="center")

        tree_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self._preview_tree.yview)
        self._preview_tree.configure(yscrollcommand=tree_scroll.set)

        self._preview_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        paned.add(preview_frame, weight=1)

        # Right: log area
        log_frame = ttk.LabelFrame(paned, text="Log", padding=5)
        self._log_text = tk.Text(
            log_frame, wrap="word", height=15, state="disabled",
            font=("Courier", 10), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="#d4d4d4",
        )
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)

        self._log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        paned.add(log_frame, weight=1)

    # ── Status bar ─────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        """Build the bottom status bar with progress indicator."""
        frame = ttk.Frame(self._root, padding=(self.PAD, 0, self.PAD, self.PAD))
        frame.grid(row=3, column=0, sticky="ew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, textvariable=self._status_var, style="Status.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self._progress_bar = ttk.Progressbar(
            frame, variable=self._progress_var, maximum=100, length=300
        )
        self._progress_bar.grid(row=0, column=1, sticky="ew", padx=(10, 0))

    # ── Event handlers ─────────────────────────────────────────────────

    def _browse_folder(self) -> None:
        """Open a folder selection dialog."""
        folder = filedialog.askdirectory(title="Select folder to organize")
        if folder:
            self._selected_folder = Path(folder)
            self._folder_var.set(str(self._selected_folder))
            self._organizer.target_folder = self._selected_folder
            self._btn_organize.configure(state="normal")
            self._update_undo_buttons()
            self._log(f"Selected folder: {self._selected_folder}")
            self._show_preview()

    def _show_preview(self) -> None:
        """Populate the preview tree with classified files."""
        if not self._selected_folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        # Clear existing items
        for item in self._preview_tree.get_children():
            self._preview_tree.delete(item)

        try:
            classified = self._organizer.preview(self._selected_folder)
        except (FileNotFoundError, PermissionError, NotADirectoryError) as e:
            messagebox.showerror("Error", str(e))
            return

        total_files = 0
        for category, files in sorted(classified.items()):
            cat_id = self._preview_tree.insert(
                "", "end", text=f"📁 {category}", values=(len(files),), open=False
            )
            for fp in sorted(files, key=lambda p: p.name.lower()):
                self._preview_tree.insert(cat_id, "end", text=f"  📄 {fp.name}", values=("",))
            total_files += len(files)

        self._log(f"Preview: {total_files} file(s) in {len(classified)} categorie(s)")

    def _start_organize(self) -> None:
        """Begin the organization process in a background thread."""
        if not self._selected_folder:
            return

        self._btn_organize.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._btn_undo.configure(state="disabled")
        self._btn_undo_all.configure(state="disabled")
        self._progress_var.set(0)
        self._status_var.set("Organizing…")
        self._log("Starting organization…")

        self._organize_thread = threading.Thread(target=self._run_organize, daemon=True)
        self._organize_thread.start()

    def _run_organize(self) -> None:
        """Run the organization (called from background thread)."""
        try:
            moved, skipped, errors = self._organizer.organize(
                self._selected_folder, progress_callback=self._on_progress
            )
            self._root.after(0, self._on_organize_complete, moved, skipped, errors)
        except Exception as e:
            self._root.after(0, self._on_organize_error, str(e))

    def _on_progress(self, current: int, total: int, message: str) -> None:
        """Handle progress updates from the organizer (called from worker thread)."""
        if total > 0:
            pct = (current / total) * 100
        else:
            pct = 0
        self._root.after(0, self._update_progress, pct, message)

    def _update_progress(self, pct: float, message: str) -> None:
        """Update progress bar and log (called on main thread)."""
        self._progress_var.set(pct)
        self._status_var.set(f"Progress: {pct:.0f}%")
        self._log(message)

    def _on_organize_complete(self, moved: int, skipped: int, errors: int) -> None:
        """Handle organization completion (called on main thread)."""
        self._btn_organize.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._progress_var.set(100)
        self._status_var.set("Done")
        self._update_undo_buttons()

        summary = f"Complete — Moved: {moved} | Skipped: {skipped} | Errors: {errors}"
        self._log(summary)
        messagebox.showinfo("Organization Complete", summary)

        # Refresh preview
        self._show_preview()

    def _on_organize_error(self, error_msg: str) -> None:
        """Handle organization error (called on main thread)."""
        self._btn_organize.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._status_var.set("Error")
        self._log(f"ERROR: {error_msg}")
        messagebox.showerror("Error", error_msg)

    def _stop_organize(self) -> None:
        """Signal the organizer to stop."""
        self._organizer.stop()
        self._btn_stop.configure(state="disabled")
        self._status_var.set("Stopping…")
        self._log("Stop requested.")

    def _undo_last(self) -> None:
        """Undo the most recent file move."""
        success = self._organizer.undo_last()
        if success:
            self._log("Undo: last move reversed.")
            messagebox.showinfo("Undo", "Last move has been undone.")
        else:
            self._log("Undo: nothing to undo or failed.")
            messagebox.showwarning("Undo", "Nothing to undo or the operation failed.")
        self._update_undo_buttons()
        self._show_preview()

    def _undo_all(self) -> None:
        """Undo all recorded moves."""
        if not messagebox.askyesno("Undo All", "Reverse ALL previous moves?"):
            return

        restored, failed = self._organizer.undo_all()
        msg = f"Undo All: {restored} restored, {failed} failed."
        self._log(msg)
        messagebox.showinfo("Undo All", msg)
        self._update_undo_buttons()
        self._show_preview()

    def _update_undo_buttons(self) -> None:
        """Enable or disable undo buttons based on history."""
        has_history = self._organizer.history.record_count > 0
        state = "normal" if has_history else "disabled"
        if self._btn_undo:
            self._btn_undo.configure(state=state)
        if self._btn_undo_all:
            self._btn_undo_all.configure(state=state)

    def _log(self, message: str) -> None:
        """Append a message to the log text widget."""
        if self._log_text is None:
            return
        self._log_text.configure(state="normal")
        self._log_text.insert("end", message + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _on_close(self) -> None:
        """Handle window close: stop any running operation and destroy."""
        if self._organizer.is_running:
            self._organizer.stop()
        self._root.destroy()

    def __repr__(self) -> str:
        return f"OrganizerGUI(organizer={self._organizer!r})"
