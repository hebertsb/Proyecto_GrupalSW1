from pathlib import Path
import random

class StanfordDogsLoader:
    def __init__(self, images_dir: str = r"D:\SW1\entrenamientoperro\data\raw\stanford_dogs\Images"):
        self.images_dir = Path(images_dir)

    def get_breeds(self) -> list[str]:
        if not self.images_dir.exists():
            return []
        return sorted([d.name for d in self.images_dir.iterdir() if d.is_dir()])

    def get_random_image_by_breed(self, raza_id: str) -> Path | None:
        breed_dir = self.images_dir / raza_id
        if not breed_dir.exists() or not breed_dir.is_dir():
            return None
        images = list(breed_dir.glob("*.jpg"))
        if not images:
            return None
        return random.choice(images)

    def get_dataset_stats(self) -> dict:
        breeds = self.get_breeds()
        if not self.images_dir.exists():
            return {
                "total_razas": 0,
                "total_imagenes": 0
            }
        total_images = sum(1 for _ in self.images_dir.rglob("*.jpg"))
        return {
            "total_razas": len(breeds),
            "total_imagenes": total_images
        }
