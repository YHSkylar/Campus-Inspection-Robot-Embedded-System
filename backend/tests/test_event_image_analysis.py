from pathlib import Path
import tempfile
import unittest

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None

from app.services.system import service


@unittest.skipIf(Image is None, "Pillow not installed")
class BackendImageAnalysisIntegrationTest(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
