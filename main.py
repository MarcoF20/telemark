import sys
import os
import sv_ttk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database import init_db
from app import App

if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
