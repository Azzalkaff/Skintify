import threading
from app.database.data_manager import DataManager
from nicegui import app as nicegui_app

<<<<<<< HEAD
class AppState(BaseModel):
    # Data rutin skincare yang dipilih user
    routine: List[Dict[str, Any]] = Field(default_factory=list)
    kota: str = ""
    category: str = "All"
    page: int = 1
    wishlist: List[Dict[str, Any]] = Field(default_factory=list)
    mkt_filter: bool = False
=======
class SessionStateWrapper:
    """
    Wrapper thread-safe & session-aware untuk NiceGUI.
    Mengalihkan akses atribut AppState ke `app.storage.user` (session storage)
    secara dinamis saat dipanggil di dalam request context, dan menyediakan
    fallback thread-local jika dipanggil di luar request context.
    """
    def __init__(self):
        # Gunakan super().__setattr__ untuk menghindari infinite recursion di __setattr__
        super().__setattr__('_fallback', threading.local())
>>>>>>> 9b7123ff6ba998aab091ec6c6d8ba299e5375ba1

    def _get_fallback_dict(self):
        if not hasattr(self._fallback, 'data'):
            self._fallback.data = {}
        return self._fallback.data

    def __getattr__(self, name):
        # Nilai default untuk properti state
        defaults = {
            'routine': [],
            'kota': '',
            'category': 'All',
            'page': 1,
            'wishlist': [],
            'recent_products': [],
            'mkt_filter': False
        }
        
        try:
            # Ambil dari NiceGUI session storage (user spesifik)
            user_storage = nicegui_app.storage.user
            if name in user_storage:
                return user_storage[name]
            elif name in defaults:
                user_storage[name] = defaults[name]
                return user_storage[name]
        except (RuntimeError, AttributeError):
            # Fallback ke thread-local storage jika di luar request context (misal saat import/cli)
            fallback = self._get_fallback_dict()
            if name in fallback:
                return fallback[name]
            elif name in defaults:
                fallback[name] = defaults[name]
                return fallback[name]
                
        raise AttributeError(f"'SessionStateWrapper' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name == '_fallback':
            super().__setattr__(name, value)
            return
            
        try:
            nicegui_app.storage.user[name] = value
        except (RuntimeError, AttributeError):
            fallback = self._get_fallback_dict()
            fallback[name] = value

    def __delattr__(self, name):
        try:
            if name in nicegui_app.storage.user:
                del nicegui_app.storage.user[name]
                return
        except (RuntimeError, AttributeError):
            fallback = self._get_fallback_dict()
            if name in fallback:
                del fallback[name]
                return
        raise AttributeError(f"'SessionStateWrapper' object has no attribute '{name}'")

# Inisialisasi Singleton
data_mgr = DataManager()
state = SessionStateWrapper()
