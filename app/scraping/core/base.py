import json
import os
import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Tuple

class BaseScraper(ABC):
    """
    Base class for all marketplace scrapers to ensure consistency and maintainability.
    """
    def __init__(self, name: str):
        self.name = name
        self.results_dir = Path("data/raw")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def scrape(self, keyword: str, top_n: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Perform scraping and return (products, shops).
        """
        pass

    def save_to_json(self, data: Dict[str, Any], filename: str):
        """
        Save results to a JSON file.
        """
        filepath = self.results_dir / f"{filename}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    def random_sleep(self, min_s: float = 2.0, max_s: float = 4.0):
        """
        Random sleep to avoid being blocked.
        """
        delay = random.uniform(min_s, max_s)
        time.sleep(delay)
