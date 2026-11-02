#!/usr/bin/env python3
"""Integration tests on temporary configurations only; Python is not an installer dependency."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
ASSET = REPO / "karabiner" / "external-windows-shortcuts.json"
SOURCE = json.loads(ASSET.read_text())["rules"]


class InstallerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="mwk-test-", dir=os.environ.get("MWK_TEST_TMPDIR"))
        self.root = Path(self.temp.name)
        self.config = self.root / "config with spaces" / "karabiner.json"
        self.state = Path(str(self.config) + ".macos-windows-keyboard-state.json")
        self.foreign = {
            "description": "Existing custom rule",
            "manipulators": [{"type": "basic", "from": {"key_code": "f19"},
                              "to": [{"key_code": "escape"}]}]
        }

    def tearDown(self):
        self.temp.cleanup()

    def base(self, rules=None):
        return {"global": {"show_in_menu_bar": False},
                "profiles": [{"name": "Personal", "selected": True,
                              "devices": [{"identifiers": {"vendor_id": 1234,
                                                         "product_id": 5678,
                                                         "is_keyboard": True},
                                           "ignore": True}],
                              "complex_modifications": {
                                  "parameters": {"basic.to_if_alone_timeout_milliseconds": 200},
                                  "rules": copy.deepcopy([self.foreign] if rules is None else rules)}}]}

    def write(self, data):
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps(data, indent=2) + "\n")
        return self.config.read_bytes()

    def read(self):
        return json.loads(self.config.read_text())

    def call(self, mode="install", *args, ok=True, source=None):
        if source is None:
            command = ["/bin/bash", str(REPO / (mode + ".sh"))]
        else:
            command = ["/usr/bin/osascript", "-l", "JavaScript",
                       str(REPO / "scripts" / "manage.js"), mode, str(source)]
        result = subprocess.run(
            command + ["--config", str(self.config)] + list(args),
            text=True, capture_output=True)
        if not ok:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            return result
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_install_backup_and_uninstall_preserve_existing_and_later_changes(self):
        original = self.base()
        original_bytes = self.write(original)
        result = self.call()
        self.assertEqual(result["added_rules"], len(SOURCE))
        backup = Path(result["backup_path"])
        self.assertEqual((backup / "config.before.json").read_bytes(), original_bytes)
        self.assertFalse(json.loads((backup / "manifest.json").read_text())["state_existed"])
        installed = self.read()
        comparison = copy.deepcopy(installed)
        comparison["profiles"][0]["complex_modifications"]["rules"] = [self.foreign]
        self.assertEqual(comparison, original)
        installed["global"]["new_preference"] = True
        later = {"description": "Added later", "manipulators": self.foreign["manipulators"]}
        installed["profiles"][0]["complex_modifications"]["rules"].append(later)
        self.write(installed)
        removed = self.call("uninstall")
        self.assertEqual(removed["removed_rules"], len(SOURCE))
        final = self.read()
        self.assertEqual(final["profiles"][0]["complex_modifications"]["rules"],
                         [self.foreign, later])
        self.assertTrue(final["global"]["new_preference"])
        self.assertEqual(json.loads(self.state.read_text())["rules"], [])

    def test_install_twice_is_byte_identical_and_creates_no_second_backup(self):
        self.write(self.base())
        self.call()
        config, state = self.config.read_bytes(), self.state.read_bytes()
        backups = list((self.config.parent / "backups").rglob("manifest.json"))
        result = self.call()
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["skipped_existing_rules"], len(SOURCE))
        self.assertIsNone(result["backup_path"])
        self.assertEqual(config, self.config.read_bytes())
        self.assertEqual(state, self.state.read_bytes())
        self.assertEqual(backups, list((self.config.parent / "backups").rglob("manifest.json")))

    def test_existing_manual_rules_are_not_adopted_or_removed(self):
        original = self.write(self.base(SOURCE))
        result = self.call()
        self.assertEqual(result["skipped_existing_rules"], len(SOURCE))
        self.assertEqual(original, self.config.read_bytes())
        self.assertFalse(self.state.exists())
        result = self.call("uninstall")
        self.assertEqual(result["removed_rules"], 0)
        self.assertEqual(original, self.config.read_bytes())

    def test_disabled_manual_duplicate_with_different_description_is_preserved(self):
        manual = copy.deepcopy(SOURCE[0])
        manual["description"] = "My own language switch"
        manual["enabled"] = False
        self.write(self.base([manual]))
        result = self.call()
        self.assertEqual(result["added_rules"], len(SOURCE) - 1)
        self.assertEqual(result["skipped_existing_rules"], 1)
        self.call("uninstall")
        self.assertEqual(self.read()["profiles"][0]["complex_modifications"]["rules"], [manual])

    def test_description_conflict_aborts_without_changing_anything(self):
        conflict = copy.deepcopy(SOURCE[0])
        conflict["manipulators"][0]["to"] = [{"key_code": "escape"}]
        original = self.write(self.base([conflict]))
        self.call(ok=False)
        self.assertEqual(original, self.config.read_bytes())
        self.assertFalse(self.state.exists())

    def test_selected_profile_only_and_explicit_inactive_profile(self):
        original = self.base()
        original["profiles"].append({"name": "Other", "selected": False,
                                    "complex_modifications": {"rules": []}})
        self.write(original)
        self.call()
        current = self.read()
        self.assertEqual(current["profiles"][1], original["profiles"][1])
        self.call("install", "--profile", "Other")
        current = self.read()
        self.assertFalse(current["profiles"][1]["selected"])
        self.assertEqual(len(current["profiles"][1]["complex_modifications"]["rules"]), len(SOURCE))
        current["profiles"][0]["name"] = "Renamed after install"
        self.write(current)
        result = self.call("uninstall")
        self.assertEqual(result["removed_rules"], len(SOURCE) * 2)
        self.assertEqual(self.read()["profiles"][0]["complex_modifications"]["rules"], [self.foreign])

    def test_ambiguous_profile_requires_explicit_name(self):
        config = self.base()
        config["profiles"][0]["selected"] = False
        self.write(config)
        original = self.config.read_bytes()
        self.call(ok=False)
        self.assertEqual(original, self.config.read_bytes())
        self.call("install", "--profile", "Personal")

    def test_invalid_config_and_state_are_not_replaced(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text("{not json")
        original = self.config.read_bytes()
        self.call(ok=False)
        self.assertEqual(original, self.config.read_bytes())
        original = self.write(self.base())
        self.state.write_text("{bad state")
        self.call(ok=False)
        self.assertEqual(original, self.config.read_bytes())
        self.assertEqual(self.state.read_text(), "{bad state")

    def test_symlink_and_broken_symlink_are_refused(self):
        self.config.parent.mkdir(parents=True)
        target = self.root / "real.json"
        target.write_text(json.dumps(self.base()))
        original = target.read_bytes()
        self.config.symlink_to(target)
        self.call(ok=False)
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(target.read_bytes(), original)
        self.config.unlink()
        self.config.symlink_to(self.root / "missing-target.json")
        self.call(ok=False)
        self.assertTrue(self.config.is_symlink())

    def test_state_symlink_is_refused(self):
        original = self.write(self.base())
        self.state.symlink_to(self.root / "missing-state.json")
        self.call(ok=False)
        self.assertEqual(original, self.config.read_bytes())

    def test_dry_run_does_not_create_directories_or_rewrite_existing_files(self):
        result = self.call("install", "--dry-run")
        self.assertEqual(result["status"], "dry-run")
        self.assertFalse(self.config.parent.exists())
        original = self.write(self.base())
        self.call("install", "--dry-run")
        self.assertEqual(original, self.config.read_bytes())
        self.assertFalse(self.state.exists())
        self.call()
        installed, state = self.config.read_bytes(), self.state.read_bytes()
        result = self.call("uninstall", "--dry-run")
        self.assertEqual(result["removed_rules"], len(SOURCE))
        self.assertEqual(installed, self.config.read_bytes())
        self.assertEqual(state, self.state.read_bytes())

    def test_fresh_install_records_absence_and_uninstall_is_repeatable(self):
        result = self.call()
        manifest = json.loads((Path(result["backup_path"]) / "manifest.json").read_text())
        self.assertFalse(manifest["config_existed"])
        self.assertFalse((Path(result["backup_path"]) / "config.before.json").exists())
        self.call("uninstall")
        self.assertEqual(self.read()["profiles"][0]["complex_modifications"]["rules"], [])
        result = self.call("uninstall")
        self.assertEqual(result["status"], "unchanged")
        self.call()

    def test_edited_owned_rule_is_kept_and_reinstallation_refuses_to_replace_it(self):
        self.write(self.base())
        self.call()
        config = self.read()
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        edited = rules[1]
        edited["manipulators"][0]["to"] = [{"key_code": "f20"}]
        self.write(config)
        result = self.call("uninstall")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["removed_rules"], len(SOURCE) - 1)
        self.assertEqual(result["preserved_edited_rules"], [edited["description"]])
        self.assertEqual(self.read()["profiles"][0]["complex_modifications"]["rules"],
                         [self.foreign, edited])
        original = self.config.read_bytes()
        self.call(ok=False)
        self.assertEqual(original, self.config.read_bytes())

    def test_toggling_enabled_does_not_prevent_uninstalling_owned_rule(self):
        self.write(self.base())
        self.call()
        config = self.read()
        config["profiles"][0]["complex_modifications"]["rules"][1]["enabled"] = False
        self.write(config)
        result = self.call("uninstall")
        self.assertEqual(result["removed_rules"], len(SOURCE))
        self.assertFalse(result["preserved_edited_rules"])

    def test_backup_failure_prevents_live_changes_and_cleans_lock(self):
        original = self.write(self.base())
        not_a_directory = self.root / "backup-is-file"
        not_a_directory.write_text("leave this file alone")
        self.call("install", "--backup-dir", str(not_a_directory), ok=False)
        self.assertEqual(original, self.config.read_bytes())
        self.assertFalse(self.state.exists())
        self.assertFalse(Path(str(self.config) + ".macos-windows-keyboard.lock").exists())

    def test_existing_lock_is_not_removed(self):
        original = self.write(self.base())
        lock = Path(str(self.config) + ".macos-windows-keyboard.lock")
        lock.mkdir()
        self.call(ok=False)
        self.assertTrue(lock.is_dir())
        self.assertEqual(original, self.config.read_bytes())

    def test_missing_or_bad_source_never_changes_config(self):
        original = self.write(self.base())
        self.call(ok=False, source=self.root / "missing-rules.json")
        bad = self.root / "bad-rules.json"
        bad.write_text('{"rules":[]}')
        self.call(ok=False, source=bad)
        self.assertEqual(original, self.config.read_bytes())
        self.assertFalse(self.state.exists())

    def test_concurrent_installers_never_leave_orphaned_or_duplicate_rules(self):
        for iteration in range(4):
            self.config = self.root / ("race-" + str(iteration)) / "karabiner.json"
            self.state = Path(str(self.config) + ".macos-windows-keyboard-state.json")
            self.write(self.base())
            command = ["/bin/bash", str(REPO / "install.sh"), "--config", str(self.config)]
            processes = [subprocess.Popen(command, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, text=True) for _ in range(2)]
            results = [(process, process.communicate(timeout=30)) for process in processes]
            self.assertTrue(any(process.returncode == 0 for process, _ in results))
            rules = self.read()["profiles"][0]["complex_modifications"]["rules"]
            self.assertEqual(len(rules), len(SOURCE) + 1)
            state = json.loads(self.state.read_text())
            self.assertEqual(len(state["rules"]), len(SOURCE))
            self.assertEqual({r["description"] for r in rules[1:]},
                             {e["rule"]["description"] for e in state["rules"]})
            self.call("uninstall")
            self.assertEqual(self.read()["profiles"][0]["complex_modifications"]["rules"],
                             [self.foreign])

    def test_recovery_when_ownership_was_written_before_config(self):
        original = self.write(self.base())
        self.call()
        self.config.write_bytes(original)
        self.call()
        self.assertEqual(len(self.read()["profiles"][0]["complex_modifications"]["rules"]), len(SOURCE) + 1)
        self.call("uninstall")
        self.assertEqual(self.read()["profiles"][0]["complex_modifications"]["rules"],
                         [self.foreign])
        self.assertEqual(json.loads(self.state.read_text())["rules"], [])

    def test_unicode_profile_and_path_preserve_existing_preferences(self):
        self.config = self.root / "\u0e17\u0e14\u0e2a\u0e2d\u0e1a" / "karabiner.json"
        self.state = Path(str(self.config) + ".macos-windows-keyboard-state.json")
        config = self.base()
        name = "\u0e42\u0e1b\u0e23\u0e44\u0e1f\u0e25\u0e4c"
        config["profiles"][0]["name"] = name
        config["global"]["unicode"] = "\u0e44\u0e17\u0e22 \U0001f642"
        self.write(config)
        self.call("install", "--profile", name)
        self.call("uninstall")
        self.assertEqual(self.read(), config)

    def test_upgrade_from_four_managed_rules_adds_only_terminal_rule(self):
        self.write(self.base())
        old_asset = self.root / "old-rules.json"
        old_asset.write_text(json.dumps({"rules": SOURCE[:-1]}))
        first = self.call(source=old_asset)
        self.assertEqual(first["added_rules"], len(SOURCE) - 1)
        before = self.config.read_bytes()
        old_rules = copy.deepcopy(self.read()["profiles"][0]["complex_modifications"]["rules"])
        result = self.call()
        self.assertEqual(result["added_rules"], 1)
        self.assertEqual(result["skipped_existing_rules"], len(SOURCE) - 1)
        self.assertEqual((Path(result["backup_path"]) / "config.before.json").read_bytes(), before)
        self.assertEqual(self.read()["profiles"][0]["complex_modifications"]["rules"][:-1], old_rules)
        self.assertEqual(len(json.loads(self.state.read_text())["rules"]), len(SOURCE))
        self.assertEqual(self.call("uninstall")["removed_rules"], len(SOURCE))
        self.assertEqual(self.read()["profiles"][0]["complex_modifications"]["rules"], [self.foreign])

    def test_upgrade_from_manual_old_rules_does_not_adopt_them(self):
        original = self.base(SOURCE[:-1])
        self.write(original)
        result = self.call()
        self.assertEqual(result["added_rules"], 1)
        self.assertEqual(result["skipped_existing_rules"], len(SOURCE) - 1)
        self.assertEqual(len(json.loads(self.state.read_text())["rules"]), 1)
        self.assertEqual(self.call("uninstall")["removed_rules"], 1)
        self.assertEqual(self.read(), original)

    def test_unknown_option_is_rejected(self):
        original = self.write(self.base())
        self.call("install", "--force", ok=False)
        self.assertEqual(original, self.config.read_bytes())


class KeyboardRuleScopeTests(unittest.TestCase):
    def outputs(self, key, app="com.apple.Safari", built_in=False, modifiers=("control",)):
        import re
        result = []
        device = {"is_keyboard": True, "is_built_in_keyboard": built_in}
        for rule in SOURCE:
            for manipulator in rule["manipulators"]:
                incoming = manipulator["from"]
                if incoming["key_code"] != key:
                    continue
                required = set(incoming.get("modifiers", {}).get("mandatory", []))
                optional = set(incoming.get("modifiers", {}).get("optional", []))
                actual = set(modifiers)
                if not required <= actual or not actual <= required | optional:
                    continue
                matched = True
                for condition in manipulator["conditions"]:
                    kind = condition["type"]
                    if kind == "device_if":
                        matched = matched and any(all(device.get(k) == v for k, v in identity.items())
                                                  for identity in condition["identifiers"])
                    elif kind in ("frontmost_application_if", "frontmost_application_unless"):
                        app_match = any(re.fullmatch(pattern, app)
                                        for pattern in condition["bundle_identifiers"])
                        matched = matched and (app_match if kind.endswith("_if") else not app_match)
                    else:
                        raise AssertionError("Unhandled condition: " + kind)
                if matched:
                    result.append(manipulator["to"])
        return result

    def test_terminal_copy_paste_without_remapping_other_control_keys(self):
        for app in ("com.apple.Terminal", "com.googlecode.iterm2"):
            for key in ("c", "v"):
                with self.subTest(app=app, key=key):
                    self.assertEqual(self.outputs(key, app),
                                     [[{"key_code": key, "modifiers": ["left_command"]}]])
            for key in ("x", "z", "a", "s", "f", "y"):
                self.assertEqual(self.outputs(key, app), [])

    def test_other_apps_keep_all_windows_shortcuts_and_builtin_is_untouched(self):
        for app in ("com.apple.Safari", "com.apple.Notes"):
            for key in ("c", "v", "x", "z", "a", "s", "f", "y"):
                target = "z" if key == "y" else key
                mods = ["left_command", "left_shift"] if key == "y" else ["left_command"]
                self.assertEqual(self.outputs(key, app), [[{"key_code": target, "modifiers": mods}]])
        for app in ("com.apple.Safari", "com.apple.Terminal", "com.googlecode.iterm2"):
            for key in ("c", "v", "x", "z", "a", "s", "f", "y"):
                self.assertEqual(self.outputs(key, app, built_in=True), [])
                self.assertEqual(self.outputs(key, app, modifiers=("control", "shift")), [])
            self.assertEqual(self.outputs("grave_accent_and_tilde", app, modifiers=()),
                             [[{"key_code": "spacebar", "modifiers": ["left_control"], "repeat": False}]])
            self.assertEqual(self.outputs("grave_accent_and_tilde", app, modifiers=("shift",)), [])
            self.assertEqual(self.outputs("grave_accent_and_tilde", app, built_in=True, modifiers=()), [])


if __name__ == "__main__":
    unittest.main()
