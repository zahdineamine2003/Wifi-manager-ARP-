"""
Tests unitaires pour WIFI Manager
Valide les modules critiques: CIDR, OUI, CSV, Ping
"""

import unittest
import tempfile
import os
import sys

# Ajoute le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import CIDRValidator, OUIDatabase, CSVExporter, PingUtils


class TestCIDRValidator(unittest.TestCase):
    """Tests pour la validation CIDR."""
    
    def test_valid_cidr(self):
        """Teste les CIDR valides."""
        self.assertTrue(CIDRValidator.is_valid("192.168.1.0/24"))
        self.assertTrue(CIDRValidator.is_valid("10.0.0.0/8"))
        self.assertTrue(CIDRValidator.is_valid("172.16.0.0/12"))
        self.assertTrue(CIDRValidator.is_valid("0.0.0.0/0"))
    
    def test_invalid_cidr(self):
        """Teste les CIDR invalides."""
        self.assertFalse(CIDRValidator.is_valid("256.256.256.256/32"))
        self.assertFalse(CIDRValidator.is_valid("192.168.1.0/33"))
        self.assertFalse(CIDRValidator.is_valid("invalid"))
        self.assertFalse(CIDRValidator.is_valid(""))
        self.assertFalse(CIDRValidator.is_valid(None))
    
    def test_parse_cidr(self):
        """Teste le parsing CIDR."""
        net = CIDRValidator.parse("192.168.1.0/24")
        self.assertIsNotNone(net)
        self.assertEqual(str(net), "192.168.1.0/24")
        
        net = CIDRValidator.parse("invalid")
        self.assertIsNone(net)
    
    def test_suggestion(self):
        """Teste la suggestion CIDR."""
        suggestion = CIDRValidator.get_suggestion()
        self.assertIsNotNone(suggestion)
        self.assertTrue(CIDRValidator.is_valid(suggestion))
        self.assertIn("/24", suggestion)  # Généralement /24 par défaut


class TestPingUtils(unittest.TestCase):
    """Tests pour les utilitaires Ping."""
    
    def test_validate_ip(self):
        """Teste la validation d'IP."""
        self.assertTrue(PingUtils.validate_ip("192.168.1.1"))
        self.assertTrue(PingUtils.validate_ip("10.0.0.0"))
        self.assertTrue(PingUtils.validate_ip("255.255.255.255"))
        
        self.assertFalse(PingUtils.validate_ip("256.1.1.1"))
        self.assertFalse(PingUtils.validate_ip("1.1.1"))
        self.assertFalse(PingUtils.validate_ip("invalid"))
        self.assertFalse(PingUtils.validate_ip(""))
    
    def test_ping_command(self):
        """Teste la commande ping appropriée."""
        cmd, param = PingUtils.get_ping_command()
        self.assertIsNotNone(cmd)
        self.assertIsNotNone(param)
        self.assertIn(cmd, ['ping'])
        self.assertIn(param, ['-n', '-c'])  # Windows vs Linux/Mac


class TestOUIDatabase(unittest.TestCase):
    """Tests pour la base OUI."""
    
    def test_oui_initialization(self):
        """Teste l'initialisation de la DB OUI."""
        # Ne télécharge pas automatiquement (trop long)
        db = OUIDatabase(auto_download=False)
        self.assertIsNotNone(db)
    
    def test_oui_lookup_empty(self):
        """Teste le lookup avec DB vide."""
        db = OUIDatabase(auto_download=False)
        
        # Doit retourner "Unknown" si MAC invalide
        vendor = db.lookup("")
        self.assertEqual(vendor, "Unknown")
        
        # Doit retourner "Unknown" si pas de cache
        vendor = db.lookup("00:11:22:33:44:55")
        self.assertEqual(vendor, "Unknown")


class TestCSVExporter(unittest.TestCase):
    """Tests pour l'export CSV."""
    
    def test_csv_export_empty(self):
        """Teste l'export CSV vide."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            success = CSVExporter.export([], filepath)
            self.assertTrue(success)
            
            # Vérifie que le fichier a été créé
            self.assertTrue(os.path.exists(filepath))
            
            # Vérifie le contenu
            with open(filepath, 'r') as f:
                content = f.read()
                self.assertIn("Index", content)
                self.assertIn("IP", content)
                self.assertIn("MAC", content)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    def test_csv_export_with_data(self):
        """Teste l'export CSV avec données."""
        devices = [
            {'ip': '192.168.1.1', 'mac': '00:11:22:33:44:55', 'vendor': 'Router', 'ping': 2.5},
            {'ip': '192.168.1.10', 'mac': 'AA:BB:CC:DD:EE:FF', 'vendor': 'PC', 'ping': 5.0},
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            success = CSVExporter.export(devices, filepath)
            self.assertTrue(success)
            
            # Vérifie le contenu
            with open(filepath, 'r') as f:
                lines = f.readlines()
                self.assertEqual(len(lines), 3)  # Header + 2 data rows
                self.assertIn("192.168.1.1", lines[1])
                self.assertIn("Router", lines[1])
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    def test_csv_filename(self):
        """Teste la génération du nom de fichier."""
        filename = CSVExporter.get_default_filename()
        self.assertIsNotNone(filename)
        self.assertTrue(filename.startswith("scan_results_"))
        self.assertTrue(filename.endswith(".csv"))


class TestAppConfig(unittest.TestCase):
    """Tests pour la configuration."""
    
    def test_config_values(self):
        """Teste les valeurs de config."""
        from scanner import AppConfig
        
        self.assertEqual(AppConfig.DEFAULT_TIMEOUT, 2)
        self.assertEqual(AppConfig.WINDOW_WIDTH, 1000)
        self.assertEqual(AppConfig.WINDOW_HEIGHT, 600)
        self.assertIn("WIFI Manager", AppConfig.WINDOW_TITLE)


def run_tests():
    """Lance tous les tests."""
    # Crée la suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajoute les tests
    suite.addTests(loader.loadTestsFromTestCase(TestCIDRValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestPingUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestOUIDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestCSVExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestAppConfig))
    
    # Lance les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Retourne le code de sortie
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
