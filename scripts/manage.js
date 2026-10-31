/* Filesystem-only JXA: no UI automation, network requests, or extra runtime. */
ObjC.import("Foundation");
ObjC.bindFunction("rename", ["int", ["string", "string"]]);
ObjC.bindFunction("mkdir", ["int", ["string", "int"]]);
ObjC.bindFunction("rmdir", ["int", ["string"]]);

var fm = $.NSFileManager.defaultManager;
var packageName = "macos-windows-keyboard";

function fail(message) { throw new Error(message); }
function object(value) { return value !== null && typeof value === "object" && !Array.isArray(value); }
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function uuid() { return ObjC.unwrap($.NSUUID.UUID.UUIDString).replace(/-/g, "").toLowerCase(); }
function absolute(path) {
    if (!path || typeof path !== "string") fail("A non-empty path is required.");
    if (path.charAt(0) !== "/") path = ObjC.unwrap(fm.currentDirectoryPath) + "/" + path;
    return ObjC.unwrap($(path).stringByStandardizingPath);
}
function parent(path) { return ObjC.unwrap($(path).stringByDeletingLastPathComponent); }
function attributes(path) {
    var error = Ref();
    var value = fm.attributesOfItemAtPathError(path, error);
    if (ObjC.unwrap(value) !== undefined) return value;
    if (fm.fileExistsAtPath(path)) fail("Cannot inspect file: " + path);
    return null;
}
function snapshot(path) {
    var attrs = attributes(path);
    if (!attrs) return { exists: false, text: null, mode: 384 };
    var type = ObjC.unwrap(attrs.objectForKey($.NSFileType));
    if (type !== "NSFileTypeRegular") fail("Refusing a symlink or non-regular file: " + path);
    var error = Ref();
    var text = $.NSString.stringWithContentsOfFileEncodingError(path, $.NSUTF8StringEncoding, error);
    if (ObjC.unwrap(text) === undefined) fail("Cannot read UTF-8 file: " + path);
    return {
        exists: true,
        text: ObjC.unwrap(text),
        mode: Number(ObjC.unwrap(attrs.objectForKey($.NSFilePosixPermissions)))
    };
}
function parse(text, label) {
    try { return JSON.parse(text); } catch (e) { fail("Invalid JSON in " + label + ": " + e.message); }
}
function permissions(mode) {
    return $.NSDictionary.dictionaryWithObjectForKey($(mode), $.NSFilePosixPermissions);
}
function mkdir(path, recursive) {
    var error = Ref();
    if (!fm.createDirectoryAtPathWithIntermediateDirectoriesAttributesError(path, recursive, permissions(448), error))
        fail("Cannot create directory: " + path);
}
function ensureDirectory(path) {
    var attrs = attributes(path);
    if (attrs) {
        if (ObjC.unwrap(attrs.objectForKey($.NSFileType)) !== "NSFileTypeDirectory")
            fail("Expected a real directory, not a symlink: " + path);
    } else mkdir(path, true);
}
function removeOwnTemporary(path) {
    if (attributes(path)) fm.removeItemAtPathError(path, Ref());
}
function atomicWrite(path, text, mode) {
    var temp = parent(path) + "/.mwk-" + uuid() + ".tmp";
    var data = $(text).dataUsingEncoding($.NSUTF8StringEncoding);
    if (attributes(temp)) fail("Unexpected temporary file collision.");
    try {
        if (!fm.createFileAtPathContentsAttributes(temp, data, permissions(mode)))
            fail("Cannot write temporary file for " + path);
        var actual = $.NSData.dataWithContentsOfFile(temp);
        if (ObjC.unwrap(actual) === undefined || !actual.isEqualToData(data)) fail("Temporary file verification failed.");
        if (Number($.rename(temp, path)) !== 0) fail("Atomic rename failed for " + path);
    } finally { removeOwnTemporary(temp); }
}
function unchanged(path, before) {
    var now = snapshot(path);
    if (now.exists !== before.exists || now.text !== before.text)
        fail("File changed during this operation; close Karabiner Settings and retry: " + path);
}
function backupCopy(source, destination) {
    var error = Ref();
    if (!fm.copyItemAtPathToPathError(source, destination, error))
        fail("Backup failed: " + source);
    var original = $.NSData.dataWithContentsOfFile(source);
    var saved = $.NSData.dataWithContentsOfFile(destination);
    if (ObjC.unwrap(original) === undefined || ObjC.unwrap(saved) === undefined || !original.isEqualToData(saved)) fail("Backup verification failed.");
}
function stable(value) {
    if (Array.isArray(value)) return "[" + value.map(stable).join(",") + "]";
    if (object(value)) return "{" + Object.keys(value).sort().map(function (key) {
        return JSON.stringify(key) + ":" + stable(value[key]);
    }).join(",") + "}";
    return JSON.stringify(value);
}
function semantic(rule) {
    var value = copy(rule);
    delete value.description;
    delete value.enabled;
    return stable(value);
}
function validateConfig(config) {
    if (!object(config) || !Array.isArray(config.profiles) || !config.profiles.length)
        fail("Configuration must contain a non-empty profiles array.");
    config.profiles.forEach(function (profile) {
        if (!object(profile)) fail("Invalid profile.");
        if (profile.complex_modifications !== undefined) {
            if (!object(profile.complex_modifications)) fail("Invalid complex_modifications.");
            if (profile.complex_modifications.rules !== undefined &&
                !Array.isArray(profile.complex_modifications.rules)) fail("Invalid rules array.");
        }
    });
}
function rulesOf(profile) {
    return profile.complex_modifications && profile.complex_modifications.rules || [];
}
function profileFor(config, name) {
    var matches = config.profiles.filter(function (p) {
        return name !== null ? p.name === name : p.selected === true;
    });
    if (matches.length !== 1)
        fail(name !== null ? "Profile name must match exactly one profile." :
             "Exactly one profile must be selected; alternatively use --profile NAME.");
    return matches[0];
}
function loadState(before, configPath) {
    if (!before.exists) return { version: 1, config_path: configPath, token: uuid(), rules: [] };
    var state = parse(before.text, "installer state");
    if (!object(state) || state.version !== 1 || state.config_path !== configPath ||
        !/^[0-9a-f]{32}$/.test(state.token) || !Array.isArray(state.rules))
        fail("Invalid or incompatible installer state; do not delete it before checking backups.");
    var seen = Object.create(null);
    state.rules.forEach(function (entry) {
        if (!object(entry) || !object(entry.rule) || typeof entry.rule.description !== "string" ||
            entry.rule.description.indexOf("[" + packageName + ":" + state.token + ":") !== 0 ||
            seen[entry.rule.description]) fail("Invalid ownership entry in installer state.");
        seen[entry.rule.description] = true;
    });
    return state;
}
function usage() {
    return "Usage: bash install.sh [--dry-run] [--config FILE] [--profile NAME] [--backup-dir DIR]\n" +
        "       bash uninstall.sh [--dry-run] [--config FILE] [--backup-dir DIR]\n" +
        "No sudo. Close Karabiner Settings before applying changes.\n" +
        "Default config: ~/.config/karabiner/karabiner.json\n" +
        "Backups: CONFIG_DIRECTORY/backups/macos-windows-keyboard/\n" +
        "State: CONFIG_FILE.macos-windows-keyboard-state.json\n" +
        "Uninstall scans all profiles, preserving edited managed rules and all pre-existing rules.";
}

function run(argv) {
    var mode = argv[0], sourcePath = argv[1];
    if (mode !== "install" && mode !== "uninstall") fail("Unknown operation.");
    var env = $.NSProcessInfo.processInfo.environment;
    var home = ObjC.unwrap(env.objectForKey("HOME")) || ObjC.unwrap($.NSHomeDirectory());
    var options = { config: home + "/.config/karabiner/karabiner.json", profile: null, backup: null, dry: false };
    for (var i = 2; i < argv.length; i++) {
        var arg = argv[i];
        if (arg === "--help" || arg === "-h") return usage();
        if (arg === "--dry-run") { options.dry = true; continue; }
        if (arg !== "--config" && arg !== "--profile" && arg !== "--backup-dir") fail("Unknown option: " + arg);
        if (++i >= argv.length || !argv[i] || argv[i].indexOf("--") === 0) fail("Missing value for " + arg);
        if (arg === "--config") options.config = argv[i];
        if (arg === "--profile") options.profile = argv[i];
        if (arg === "--backup-dir") options.backup = argv[i];
    }
    if (mode === "uninstall" && options.profile !== null)
        fail("Uninstall uses recorded ownership across all profiles; omit --profile.");
    var configPath = absolute(options.config);
    var statePath = configPath + "." + packageName + "-state.json";
    var lockPath = configPath + "." + packageName + ".lock";
    var before = snapshot(configPath), stateBefore = snapshot(statePath);
    var state = loadState(stateBefore, configPath), nextState = copy(state);
    var config = before.exists ? parse(before.text, configPath) : {
        profiles: [{ name: "Default profile", selected: true, complex_modifications: { rules: [] } }]
    };
    if (!before.exists && mode === "uninstall" && state.rules.length)
        fail("Configuration is missing but ownership state remains; check backups before proceeding.");
    validateConfig(config);
    var next = copy(config);
    var report = {
        operation: mode, status: "unchanged", config_path: configPath,
        state_path: statePath, added_rules: 0, skipped_existing_rules: 0,
        removed_rules: 0, preserved_edited_rules: [], backup_path: null
    };
    var configChanged = false;
    if (mode === "install") {
        var sourceBefore = snapshot(absolute(sourcePath));
        if (!sourceBefore.exists) fail("Rule file is missing.");
        var source = parse(sourceBefore.text, sourcePath);
        if (!object(source) || !Array.isArray(source.rules) || !source.rules.length) fail("Rule file has no rules.");
        var sourceDescriptions = Object.create(null);
        source.rules.forEach(function (rule) {
            if (!object(rule) || typeof rule.description !== "string" || !rule.description ||
                !Array.isArray(rule.manipulators) || !rule.manipulators.length ||
                sourceDescriptions[rule.description]) fail("Invalid or duplicate rule in the rule file.");
            sourceDescriptions[rule.description] = true;
        });
        /* Refuse to replace a managed rule that the user has customized. */
        state.rules.forEach(function (entry) {
            next.profiles.forEach(function (p) {
                rulesOf(p).forEach(function (rule) {
                    if (object(rule) && rule.description === entry.rule.description &&
                        semantic(rule) !== semantic(entry.rule))
                        fail("An installed rule was edited. Keep it or remove it manually before reinstalling: " + rule.description);
                });
            });
        });
        var target = profileFor(next, options.profile);
        if (!target.complex_modifications) target.complex_modifications = {};
        if (!target.complex_modifications.rules) target.complex_modifications.rules = [];
        var targetRules = target.complex_modifications.rules;
        source.rules.forEach(function (desired) {
            if (targetRules.some(function (rule) { return object(rule) && semantic(rule) === semantic(desired); })) {
                report.skipped_existing_rules++;
                return;
            }
            if (targetRules.some(function (rule) { return object(rule) && rule.description === desired.description; }))
                fail("A different rule already uses this description; existing rule was left untouched: " + desired.description);
            var added = copy(desired);
            added.description = "[" + packageName + ":" + state.token + ":" + uuid().slice(0, 12) + "] " + desired.description;
            targetRules.push(added);
            nextState.rules.push({ rule: copy(added) });
            report.added_rules++;
        });
        configChanged = report.added_rules > 0;
    } else {
        var owned = Object.create(null), retained = Object.create(null);
        state.rules.forEach(function (entry) { owned[entry.rule.description] = entry; });
        next.profiles.forEach(function (p) {
            if (!p.complex_modifications || !p.complex_modifications.rules) return;
            p.complex_modifications.rules = p.complex_modifications.rules.filter(function (rule) {
                var entry = object(rule) && owned[rule.description];
                if (!entry) return true;
                if (semantic(rule) !== semantic(entry.rule)) {
                    retained[rule.description] = true;
                    return true;
                }
                report.removed_rules++;
                return false;
            });
        });
        nextState.rules = state.rules.filter(function (entry) { return retained[entry.rule.description]; });
        report.preserved_edited_rules = Object.keys(retained);
        configChanged = report.removed_rules > 0;
    }
    var stateChanged = stable(nextState) !== stable(state);
    if (!configChanged && !stateChanged) {
        if (report.preserved_edited_rules.length) report.status = "partial";
        return JSON.stringify(report, null, 2);
    }
    if (options.dry) {
        report.status = "dry-run";
        return JSON.stringify(report, null, 2);
    }
    ensureDirectory(parent(configPath));
    if (attributes(lockPath)) fail("Installer lock exists. Check no installer is running before removing: " + lockPath);
    if (Number($.mkdir(lockPath, 448)) !== 0)
        fail("Another installer holds the lock, or the lock cannot be created: " + lockPath);
    try {
        unchanged(configPath, before);
        unchanged(statePath, stateBefore);
        var backupRoot = absolute(options.backup || parent(configPath) + "/backups/" + packageName);
        ensureDirectory(backupRoot);
        var backupPath = backupRoot + "/" + new Date().toISOString().replace(/[:.]/g, "-") + "-" + uuid().slice(0, 12);
        mkdir(backupPath, false);
        if (before.exists) backupCopy(configPath, backupPath + "/config.before.json");
        if (stateBefore.exists) backupCopy(statePath, backupPath + "/state.before.json");
        atomicWrite(backupPath + "/manifest.json", JSON.stringify({
            version: 1, operation: mode, config_path: configPath, state_path: statePath,
            config_existed: before.exists, state_existed: stateBefore.exists,
            created_at: new Date().toISOString()
        }, null, 2) + "\n", 384);
        report.backup_path = backupPath;
        unchanged(configPath, before);
        unchanged(statePath, stateBefore);
        /* Write ownership first, so an interrupted config write cannot leave unrecorded rules. */
        if (stateChanged) atomicWrite(statePath, JSON.stringify(nextState, null, 4) + "\n", 384);
        unchanged(configPath, before);
        if (configChanged) atomicWrite(configPath, JSON.stringify(next, null, 4) + "\n", before.mode);
        report.status = report.preserved_edited_rules.length ? "partial" : "changed";
        return JSON.stringify(report, null, 2);
    } finally { $.rmdir(lockPath); }
}
