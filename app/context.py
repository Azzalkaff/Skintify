from app.database.data_manager import DataManager
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class AppState(BaseModel):
    # Data rutin skincare yang dipilih user
    routine: List[Dict[str, Any]] = Field(default_factory=list)
    kota: str = ""
    category: str = "All"
    page: int = 1
    wishlist: List[Dict[str, Any]] = Field(default_factory=list)
    mkt_filter: bool = False

# Singleton: Hanya dimuat sekali ke memori saat server berjalan
# Objek ini akan di-share ke semua halaman
data_mgr = DataManager()
state = AppState()
