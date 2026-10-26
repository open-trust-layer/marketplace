"""Source-only regression for strict Windows PostgreSQL evaluator process matching.

No credential access, database connection, browser or service execution.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools" / "marketplace_evaluator_operator_probe.ps1"


class OperatorPostgresDataDirectoryTests(unittest.TestCase):
    def test_launcher_uses_strict_data_directory_helper(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("function TestExactEvaluatorPostgresDataDirectory(", source)
        self.assertIn(
            "-not (TestExactEvaluatorPostgresDataDirectory "
            "$server.CommandLine $expectedDataDirectory)",
            source,
        )
        self.assertIn("$server.Name -ne 'postgres.exe'", source)
        self.assertIn("-LocalAddress '127.0.0.1' -LocalPort 15432", source)
        self.assertIn("if ($listener.Count -ne 1)", source)
        self.assertIn("if ($confirmation -cne 'RUN LOCAL READONLY PROBE')", source)
        self.assertNotIn(
            "$server.CommandLine -notlike ('*' + $expectedDataDirectory + '*')", source
        )

    def test_powershell_helper_rejects_decoys_but_accepts_slash_forms(self) -> None:
        executable = shutil.which("powershell.exe") or shutil.which("pwsh")
        if not executable:
            self.skipTest("Windows PowerShell executable unavailable")
        source = LAUNCHER.read_text(encoding="utf-8")
        start = source.index("function TestExactEvaluatorPostgresDataDirectory(")
        stop = source.index("\nfunction AssertCleanExactGit(", start)
        function_source = source[start:stop]
        cases = r"""
$expected = 'D:\MarketplaceEvaluatorFresh\pgdata'
$cases = @(
  @{ name='exact-backslash'; line='postgres.exe -D D:\MarketplaceEvaluatorFresh\pgdata -p 15432'; accept=$true },
  @{ name='exact-slash'; line='postgres.exe -D D:/MarketplaceEvaluatorFresh/pgdata -p 15432'; accept=$true },
  @{ name='quoted-backslash'; line='postgres.exe -D "D:\MarketplaceEvaluatorFresh\pgdata" -p 15432'; accept=$true },
  @{ name='quoted-slash'; line='postgres.exe -D "D:/MarketplaceEvaluatorFresh/pgdata" -p 15432'; accept=$true },
  @{ name='case-insensitive'; line='postgres.exe -D d:/marketplaceevaluatorfresh/PGDATA -p 15432'; accept=$true },
  @{ name='other-drive'; line='postgres.exe -D E:/MarketplaceEvaluatorFresh/pgdata -p 15432'; accept=$false },
  @{ name='other-directory'; line='postgres.exe -D D:/MarketplaceEvaluatorFresh/pgdata-other -p 15432'; accept=$false },
  @{ name='subdirectory'; line='postgres.exe -D D:/MarketplaceEvaluatorFresh/pgdata/other -p 15432'; accept=$false },
  @{ name='different-d-plus-decoy'; line='postgres.exe -D E:/other --config-file=D:/MarketplaceEvaluatorFresh/pgdata'; accept=$false },
  @{ name='missing-d-plus-decoy'; line='postgres.exe --config-file=D:/MarketplaceEvaluatorFresh/pgdata'; accept=$false },
  @{ name='embedded-d'; line='postgres.exe --fake-D D:/MarketplaceEvaluatorFresh/pgdata'; accept=$false },
  @{ name='missing-command'; line=$null; accept=$false },
  @{ name='empty-command'; line=''; accept=$false }
)
foreach ($test in $cases) {
    $observed = TestExactEvaluatorPostgresDataDirectory $test.line $expected
    if ($observed -ne $test.accept) { throw ('CASE_FAILED:' + $test.name) }
}
'STRICT_EVALUATOR_D_PATH_CHECK_13_PASS'
"""
        result = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-Command", function_source + cases],
            check=False,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-1400:])
        self.assertIn("STRICT_EVALUATOR_D_PATH_CHECK_13_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
