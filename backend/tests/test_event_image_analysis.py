from pathlib import Path
import tempfile
import unittest

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None

from app.services.system import service
from app.config import settings
from app.db import init_db


@unittest.skipIf(Image is None, "Pillow not installed")
class BackendImageAnalysisIntegrationTest(unittest.TestCase):
    def make_striped_image(self, path: Path, mode: str) -> None:
        image = Image.new('RGB', (96, 96), (0, 0, 0))
        for x in range(96):
            for y in range(96):
                if mode == 'vertical':
                    on = (x // 8) % 2 == 0
                elif mode == 'horizontal':
                    on = (y // 8) % 2 == 0
                else:
                    on = ((x + y) // 8) % 2 == 0
                image.putpixel((x, y), (240, 240, 240) if on else (10, 10, 10))
        image.save(path)

    def test_fire_image_enriches_detection_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / 'fire_sample.jpg'
            image = Image.new('RGB', (160, 160), (8, 8, 8))
            for x in range(40, 120):
                for y in range(20, 140):
                    image.putpixel((x, y), (255, 170, 20))
            image.save(image_path)

            enriched = service.enrich_detection_with_backend_image_analysis(
                {
                    'snapshot_url': str(image_path),
                    'image_features': {},
                    'payload': {},
                }
            )

            self.assertEqual(
                enriched['payload']['backend_image_analysis']['status'],
                'completed',
            )
            self.assertGreater(
                float(enriched['image_features']['fire_score']),
                0.5,
            )
            self.assertTrue(enriched['image_features']['flame_detected'])

            inference = service.infer_event_from_image(enriched)
            self.assertEqual(inference['event_type'], 'fire')

    def test_face_whitelist_match_suppresses_alarm(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            old_database_url = settings.database_url
            settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
            try:
                init_db()
                face_path = tmp_path / 'security.jpg'
                self.make_striped_image(face_path, 'vertical')
                service.upsert_known_face(
                    {
                        'face_id': 'security',
                        'name': 'Security',
                        'role': 'security',
                        'image_path': str(face_path),
                    }
                )

                result = service.detect_event(
                    {
                        'event_type': 'unauthorized_person',
                        'image_url': str(face_path),
                        'snapshot_url': str(face_path),
                        'image_tags': ['face'],
                        'image_features': {'face_check_requested': True},
                        'payload': {},
                    }
                )

                self.assertFalse(result['confirmed'])
                self.assertEqual(result['status'], 'authorized_person')
                self.assertEqual(result['inference']['event_type'], 'authorized_person')
            finally:
                settings.database_url = old_database_url

    def test_face_whitelist_miss_creates_unauthorized_alarm(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            old_database_url = settings.database_url
            settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
            old_detection_threshold = settings.detection_confidence_threshold
            settings.detection_confidence_threshold = 0.9
            try:
                init_db()
                whitelist_path = tmp_path / 'security.jpg'
                unknown_path = tmp_path / 'unknown.jpg'
                self.make_striped_image(whitelist_path, 'vertical')
                self.make_striped_image(unknown_path, 'horizontal')
                service.upsert_known_face(
                    {
                        'face_id': 'security',
                        'name': 'Security',
                        'role': 'security',
                        'image_path': str(whitelist_path),
                    }
                )

                result = service.detect_event(
                    {
                        'event_type': 'unauthorized_person',
                        'image_url': str(unknown_path),
                        'snapshot_url': str(unknown_path),
                        'image_tags': ['face'],
                        'image_features': {'face_check_requested': True},
                        'payload': {},
                    }
                )

                self.assertTrue(result['confirmed'])
                self.assertEqual(result['event']['event_type'], 'unauthorized_person')
                self.assertEqual(result['event']['status'], 'unhandled')
                self.assertEqual(result['inference']['event_type'], 'unauthorized_person')
            finally:
                settings.database_url = old_database_url
                settings.detection_confidence_threshold = old_detection_threshold


if __name__ == '__main__':
    unittest.main()
