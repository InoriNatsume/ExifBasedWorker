from __future__ import annotations

import tkinter as tk

from .app import FilenameValueExtractorApp


def main() -> None:
    root = tk.Tk()
    FilenameValueExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

